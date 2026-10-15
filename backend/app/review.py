"""Human review muna bago evidence retrieval o feedback-based training."""
import argparse
import sqlite3
import sys
import textwrap
from datetime import datetime, timezone
from typing import Callable

from . import db
from .pipeline import evidence_index

STATUSES = ("Pending", "Validated", "Rejected")
LABELS = ("Reliable", "Misinformation")


# Kunin ang current UTC timestamp para sa review log.
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Bilangin ang evidence ayon sa review status.
def evidence_stats(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {s: 0 for s in STATUSES}
    for row in conn.execute("SELECT review_status, COUNT(*) FROM evidence GROUP BY review_status"):
        counts[row[0]] = row[1]
    return counts


# Ilista ang evidence gamit ang status, source at search filters.
def list_evidence(conn, status="Pending", limit=20, offset=0, search=None, source=None) -> list[sqlite3.Row]:
    sql, args = "SELECT * FROM evidence WHERE review_status = ?", [status]
    if source:
        sql += " AND LOWER(source_name) = LOWER(?)"
        args.append(source.strip())
    if search:
        sql += " AND (evidence_text LIKE ? OR topic LIKE ?)"
        args += [f"%{search}%", f"%{search}%"]
    return conn.execute(sql + " ORDER BY evidence_id LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()


def set_evidence_status(conn: sqlite3.Connection, ids: list[int], status: str, reviewer: str,
                        note: str | None = None) -> int:
    """I-update ang status, reviewer at note; papalitan ang dating note."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if not reviewer.strip():
        raise ValueError("reviewer is required (audit trail)")
    with conn:
        changed = 0
        for evidence_id in ids:
            cur = conn.execute(
                "UPDATE evidence SET review_status = ?, reviewed_by = ?, reviewed_at = ?, updated_at = ?, "
                "review_note = ? WHERE evidence_id = ?",
                (status, reviewer, _now(), _now(), (note or "").strip() or None, evidence_id))
            changed += cur.rowcount
    if changed != len(ids):
        raise ValueError(f"{len(ids) - changed} evidence id(s) not found")
    return changed


# Ipakita ang passage, source at review details.
def _show(row: sqlite3.Row, out: Callable[[str], None]) -> None:
    out(f"--- evidence {row['evidence_id']} [{row['review_status']}] ---")
    out(f"source : {row['source_name']}  {row['source_url']}")
    out(f"topic  : {row['topic']}")
    out(f"date   : {row['publication_date'] or 'unknown'}")
    if row["reviewed_by"]:
        out(f"review : {row['reviewed_by']} at {row['reviewed_at']}")
    if row["review_note"]:
        out(f"note   : {row['review_note']}")
    out(textwrap.fill(row["evidence_text"], width=100, initial_indent="  ", subsequent_indent="  "))


# Isa-isang i-review ang Pending evidence sa terminal.
def review_interactive(conn, reviewer: str, limit: int = 20, source: str | None = None, search: str | None = None,
                       input_fn: Callable[[str], str] = input, out: Callable[[str], None] = print) -> dict[str, int]:
    done = {"Validated": 0, "Rejected": 0, "skipped": 0}
    for row in list_evidence(conn, "Pending", limit, source=source, search=search):
        _show(row, out)
        while True:
            answer = input_fn("[v]alidate / [r]eject / [s]kip / [q]uit > ").strip().lower()
            if answer in ("v", "r", "s", "q"):
                break
        if answer == "q":
            break
        if answer == "s":
            done["skipped"] += 1
            continue
        status = "Validated" if answer == "v" else "Rejected"
        note = input_fn("reason for rejecting (Enter to skip) > ") if status == "Rejected" else None
        set_evidence_status(conn, [row["evidence_id"]], status, reviewer, note)
        done[status] += 1
    return done


def set_feedback_status(conn, feedback_id: int, status: str, reviewer: str,
                        label: str | None = None, notes: str | None = None) -> None:
    """Itala ang feedback review; kailangan ng label kapag Validated."""
    if status not in ("Validated", "Rejected"):
        raise ValueError("feedback status must be Validated or Rejected")
    if status == "Validated" and label not in LABELS:
        raise ValueError(f"Validated feedback needs --label {LABELS}")
    if not reviewer.strip():
        raise ValueError("reviewer is required (audit trail)")
    if conn.execute("SELECT 1 FROM feedback WHERE feedback_id = ?", (feedback_id,)).fetchone() is None:
        raise ValueError(f"feedback {feedback_id} not found")
    with conn:
        conn.execute(
            "INSERT INTO feedback_reviews (feedback_id, review_status, validated_label, reviewer, notes) "
            "VALUES (?, ?, ?, ?, ?)", (feedback_id, status, label if status == "Validated" else None, reviewer, notes))
        conn.execute("UPDATE feedback SET review_status = ? WHERE feedback_id = ?", (status, feedback_id))


# I-rebuild ang index, o ipaalam kung sadyang nilaktawan.
def _rebuild_index(conn, skip: bool, out: Callable[[str], None] = print) -> None:
    if skip:
        out("index NOT rebuilt (--no-index). Retrieval will refuse until you run: index build")
        return
    meta = evidence_index.build_index(conn)
    out(f"index rebuilt: {len(meta['ids'])} validated passage(s)")


# Patakbuhin ang evidence, feedback o index maintenance command.
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="area", required=True)

    ev = sub.add_parser("evidence").add_subparsers(dest="cmd", required=True)
    ev.add_parser("stats")
    ls = ev.add_parser("list")
    ls.add_argument("--status", default="Pending", choices=STATUSES)
    ls.add_argument("--limit", type=int, default=20)
    ls.add_argument("--offset", type=int, default=0)
    ls.add_argument("--source", help="only this source, e.g. WHO or verafiles (not case sensitive)")
    ls.add_argument("--search")
    ev.add_parser("show").add_argument("id", type=int)
    rv = ev.add_parser("review")
    rv.add_argument("--reviewer", required=True)
    rv.add_argument("--limit", type=int, default=20)
    rv.add_argument("--source", help="only this source, e.g. WHO or verafiles (not case sensitive)")
    rv.add_argument("--search", help="only passages containing this word (in text or topic)")
    rv.add_argument("--no-index", action="store_true")
    st = ev.add_parser("set")
    st.add_argument("ids", type=int, nargs="+")
    st.add_argument("--status", required=True, choices=STATUSES)
    st.add_argument("--reviewer", required=True)
    st.add_argument("--note", help="reason for this decision, stored with the passage")
    st.add_argument("--no-index", action="store_true")

    fb = sub.add_parser("feedback").add_subparsers(dest="cmd", required=True)
    fl = fb.add_parser("list")
    fl.add_argument("--status", default="Pending", choices=STATUSES)
    fl.add_argument("--limit", type=int, default=20)
    fs = fb.add_parser("set")
    fs.add_argument("id", type=int)
    fs.add_argument("--status", required=True, choices=("Validated", "Rejected"))
    fs.add_argument("--reviewer", required=True)
    fs.add_argument("--label", choices=LABELS)
    fs.add_argument("--notes")

    ix = sub.add_parser("index").add_subparsers(dest="cmd", required=True)
    ix.add_parser("status")
    ix.add_parser("build")

    args = p.parse_args(argv)
    db.init_db()
    try:
        with db.connect() as conn:
            if args.area == "evidence":
                if args.cmd == "stats":
                    print(evidence_stats(conn))
                elif args.cmd == "list":
                    for r in list_evidence(conn, args.status, args.limit, args.offset, args.search, args.source):
                        note = f"  [note: {r['review_note']}]" if r["review_note"] else ""
                        print(f"{r['evidence_id']:>5} | {r['source_name']} | {r['evidence_text'][:90]}{note}")
                elif args.cmd == "show":
                    row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (args.id,)).fetchone()
                    if row is None:
                        raise ValueError(f"evidence {args.id} not found")
                    _show(row, print)
                elif args.cmd == "review":
                    print(review_interactive(conn, args.reviewer, args.limit, args.source, args.search))
                    _rebuild_index(conn, args.no_index)
                elif args.cmd == "set":
                    print(f"{set_evidence_status(conn, args.ids, args.status, args.reviewer, args.note)} updated")
                    _rebuild_index(conn, args.no_index)
            elif args.area == "feedback":
                if args.cmd == "list":
                    for r in conn.execute("SELECT * FROM feedback WHERE review_status = ? ORDER BY feedback_id LIMIT ?",
                                          (args.status, args.limit)):
                        print(f"{r['feedback_id']:>5} | {r['user_feedback']:<8} | model={r['model_prediction']} "
                              f"evidence={r['evidence_result']} | {r['claim_text'][:80]}")
                else:
                    set_feedback_status(conn, args.id, args.status, args.reviewer, args.label, args.notes)
                    print("recorded")
            else:
                if args.cmd == "status":
                    print(evidence_index.status(conn))
                else:
                    _rebuild_index(conn, False)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
