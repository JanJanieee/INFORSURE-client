"""Turn reviewer-validated feedback into a new training dataset version (thesis sections 7 and 14).

User feedback never reaches training directly. A feedback row only counts after a person validated it with a
label (`review feedback set ... --status Validated --label ...`). Then this tool writes a NEW dataset file that is
the base dataset plus those samples, and registers it in `dataset_versions` / `dataset_version_samples`.
It never edits the base file, never overwrites an existing version, and never trains anything.

Rules for each validated feedback sample:
- text = the claim, label = the reviewer's `validated_label` (not what the user clicked);
- skipped if the same text (ignoring case and punctuation) is already in the base dataset (a different label is
  reported as a conflict that needs a person to look at it);
- if several validated feedback rows have the same text, one is kept; if their labels disagree, all are skipped.

Usage (py -m backend.app.dataset_version ...):
    create NAME --base data/training/pubhealth_v1.csv [--out-dir data/training]
    list
Then train: py -m training.run data/training/NAME.csv --version vX.Y
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from . import config, db
from training.prepare.clean import VALID_LABELS, dedupe_key, normalize_text

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SOURCE = "user_feedback"


def validated_feedback(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Feedback whose latest review is Validated, with the reviewer's label, oldest first."""
    return conn.execute(
        "SELECT f.feedback_id, f.claim_text, r.validated_label, r.reviewer, r.reviewed_at "
        "FROM feedback f JOIN feedback_reviews r "
        "  ON r.review_id = (SELECT MAX(review_id) FROM feedback_reviews WHERE feedback_id = f.feedback_id) "
        "WHERE f.review_status = 'Validated' AND r.review_status = 'Validated' "
        "ORDER BY f.feedback_id"
    ).fetchall()


def build_dataset(base: pd.DataFrame, feedback: list[sqlite3.Row]) -> tuple[pd.DataFrame, list[int], dict]:
    """Return (combined dataset, feedback_ids used, report). Pure logic: no I/O."""
    base_label = {}
    for text, label in zip(base["text"], base["label"]):
        base_label.setdefault(dedupe_key(normalize_text(text)), label)

    report = {"validated_feedback": len(feedback), "added": 0, "skipped_duplicate_of_base": 0,
              "skipped_conflict_with_base": [], "skipped_conflicting_feedback": [], "skipped_invalid_label": [],
              "skipped_duplicate_feedback": 0}

    by_key: dict[str, list[sqlite3.Row]] = {}
    for row in feedback:
        if row["validated_label"] not in VALID_LABELS:
            report["skipped_invalid_label"].append(row["feedback_id"])
            continue
        by_key.setdefault(dedupe_key(normalize_text(row["claim_text"])), []).append(row)

    new_rows, used = [], []
    for key, rows in by_key.items():
        labels = {r["validated_label"] for r in rows}
        if len(labels) > 1:
            report["skipped_conflicting_feedback"].append([r["feedback_id"] for r in rows])
            continue
        first = rows[0]
        report["skipped_duplicate_feedback"] += len(rows) - 1
        if key in base_label:
            if base_label[key] == first["validated_label"]:
                report["skipped_duplicate_of_base"] += 1
            else:
                report["skipped_conflict_with_base"].append(first["feedback_id"])
            continue
        new_rows.append({
            "text": normalize_text(first["claim_text"]), "label": first["validated_label"], "source": SOURCE,
            "unit": "claim", "label_status": "validated_by_reviewer", "origin": f"feedback:{first['feedback_id']}",
            "group": f"feedback-{first['feedback_id']}",
        })
        used.append(first["feedback_id"])

    report["added"] = len(new_rows)
    combined = pd.concat([base, pd.DataFrame(new_rows)], ignore_index=True) if new_rows else base.copy()
    return combined, used, report


def create_version(conn: sqlite3.Connection, name: str, base_csv: Path, out_dir: Path) -> dict:
    if not NAME_RE.match(name):
        raise ValueError("name may only use letters, digits, dot, dash, underscore (max 64)")
    if conn.execute("SELECT 1 FROM dataset_versions WHERE dataset_version = ?", (name,)).fetchone():
        raise ValueError(f"dataset version '{name}' already exists; pick a new name")
    out_path = out_dir / f"{name}.csv"
    if out_path.exists():
        raise ValueError(f"{out_path} already exists; pick a new name")
    if not base_csv.is_file():
        raise ValueError(f"base dataset not found: {base_csv}")

    base = pd.read_csv(base_csv, encoding="utf-8")
    missing = {"text", "label"} - set(base.columns)
    if missing:
        raise ValueError(f"base dataset is missing columns: {sorted(missing)}")
    feedback = validated_feedback(conn)
    if not feedback:
        raise ValueError("no validated feedback yet (review feedback with: review feedback set ID --status Validated "
                         "--label Reliable|Misinformation --reviewer NAME)")

    combined, used, report = build_dataset(base, feedback)
    if not used:
        raise ValueError("no new samples: every validated feedback row was skipped (see the reasons below)\n"
                         + json.dumps(report, indent=2))

    out_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False, encoding="utf-8")
    report.update({"dataset_version": name, "base": str(base_csv), "output": str(out_path),
                   "rows_base": len(base), "rows_total": len(combined),
                   "class_counts": combined["label"].value_counts().to_dict()})
    try:
        with conn:
            conn.execute(
                "INSERT INTO dataset_versions (dataset_version, description, sample_count, artifact_path) "
                "VALUES (?, ?, ?, ?)",
                (name, f"{base_csv.name} + {len(used)} validated feedback sample(s)", len(combined), str(out_path)))
            conn.executemany("INSERT INTO dataset_version_samples (dataset_version, feedback_id) VALUES (?, ?)",
                             [(name, fid) for fid in used])
    except Exception:
        out_path.unlink(missing_ok=True)  # do not leave a file that is not registered
        raise
    out_path.with_suffix(".report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("name")
    c.add_argument("--base", type=Path, required=True)
    c.add_argument("--out-dir", type=Path, default=config.ROOT / "data" / "training")
    sub.add_parser("list")
    args = p.parse_args(argv)

    db.init_db()
    try:
        with db.connect() as conn:
            if args.cmd == "list":
                for r in conn.execute(
                        "SELECT d.dataset_version, d.sample_count, d.created_at, d.description, "
                        "(SELECT COUNT(*) FROM dataset_version_samples s WHERE s.dataset_version = d.dataset_version) AS fb "
                        "FROM dataset_versions d ORDER BY d.created_at, d.dataset_version"):
                    print(f"{r['dataset_version']:<24} rows={r['sample_count']} feedback_samples={r['fb']} {r['description'] or ''}")
            else:
                print(json.dumps(create_version(conn, args.name, args.base, args.out_dir), indent=2))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
