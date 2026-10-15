"""I-import ang sourced evidence bilang Pending para sa human review."""
import argparse
import csv
import html
import re
import sqlite3
import sys
from pathlib import Path

from . import db

MAX_PASSAGE_CHARS = 600
MIN_PASSAGE_CHARS = 40

_TAG = re.compile(r"<[^>]*>")
_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_MARKUP_HINT = re.compile(r"<[a-zA-Z/!][^>]*>|&(?:[a-zA-Z]+|#\d+);|[\u200b\u200c\u200d\u2060\ufeff]")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"‘'])")
_ABBREVIATIONS = ("Fr.", "Dr.", "Mr.", "Mrs.", "Ms.", "Sr.", "Jr.", "St.", "No.", "Sec.", "vs.", "Atty.")


def clean_text(text: str) -> str:
    """Alisin ang HTML at invisible characters; ayusin ang spaces."""
    text = _TAG.sub(" ", str(text or ""))
    text = html.unescape(text)
    text = _INVISIBLE.sub("", text)
    return " ".join(text.split())


# I-check kung may markup o invisible characters.
def has_markup(text: str) -> bool:
    return bool(_MARKUP_HINT.search(text or ""))


# Hatiin sa sentences; panatilihin ang common abbreviations.
def _sentences(text: str) -> list[str]:
    merged: list[str] = []
    for part in _SENTENCE_SPLIT.split(text.strip()):
        if merged and merged[-1].endswith(_ABBREVIATIONS):
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def split_passages(text: str, max_chars: int = MAX_PASSAGE_CHARS) -> list[str]:
    """Hatiin ang article sa maiikling evidence passages."""
    passages: list[str] = []
    current = ""
    for sentence in _sentences(" ".join(text.split())):
        if current and len(current) + 1 + len(sentence) > max_chars:
            passages.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        passages.append(current)
    # Isama sa naunang passage ang maikling huling fragment.
    if len(passages) > 1 and len(passages[-1]) < MIN_PASSAGE_CHARS:
        passages[-2] = f"{passages[-2]} {passages.pop()}"
    return passages


# I-import ang CSV bilang Pending; laktawan ang duplicate passages.
def ingest_csv(conn: sqlite3.Connection, path: Path | str) -> dict[str, int]:
    stats = {"articles": 0, "passages_added": 0, "passages_skipped": 0, "rows_rejected": 0}
    # Tanggapin ang Excel BOM para tama ang column headers.
    # Nababasa rin ang plain UTF-8 CSV.
    with open(path, encoding="utf-8-sig", newline="") as f, conn:
        for row in csv.DictReader(f):
            source, url = clean_text(row.get("source")), (row.get("url") or "").strip()
            title, text = clean_text(row.get("title")), clean_text(row.get("text"))
            if not (source and url and text):
                stats["rows_rejected"] += 1  # Kailangan ang source at URL para ma-trace ang evidence.
                continue
            stats["articles"] += 1
            topic = clean_text(row.get("topic")) or title or source
            claim = clean_text(row.get("normalized_claim")) or None
            license_note = clean_text(row.get("license")) or None
            for passage in split_passages(text):
                cur = conn.execute(
                    "INSERT OR IGNORE INTO evidence "
                    "(topic, normalized_claim, evidence_text, source_name, source_url, publication_date, license_note) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (topic, claim, passage, source, url, (row.get("publication_date") or "").strip() or None, license_note),
                )
                stats["passages_added" if cur.rowcount else "passages_skipped"] += 1
    return stats


def clean_existing(conn: sqlite3.Connection) -> dict[str, int]:
    """Linisin ang Pending markup; alisin ang empty o duplicate rows."""
    stats = {"cleaned": 0, "deleted": 0}
    rows = conn.execute("SELECT evidence_id, source_url, evidence_text FROM evidence WHERE review_status = 'Pending'").fetchall()
    with conn:
        for r in rows:
            if not has_markup(r["evidence_text"]):
                continue
            cleaned = clean_text(r["evidence_text"])
            clash = cleaned and conn.execute(
                "SELECT 1 FROM evidence WHERE source_url = ? AND evidence_text = ? AND evidence_id <> ?",
                (r["source_url"], cleaned, r["evidence_id"])).fetchone()
            if not cleaned or clash:
                conn.execute("DELETE FROM evidence WHERE evidence_id = ?", (r["evidence_id"],))
                stats["deleted"] += 1
            else:
                conn.execute("UPDATE evidence SET evidence_text = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') "
                             "WHERE evidence_id = ?", (cleaned, r["evidence_id"]))
                stats["cleaned"] += 1
    return stats


# Patakbuhin ang evidence import o cleanup command.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest evidence passages as Pending.")
    parser.add_argument("csv_path", type=Path, nargs="?")
    parser.add_argument("--clean-existing", action="store_true", help="clean Pending rows that still contain markup")
    args = parser.parse_args(argv)
    if not args.csv_path and not args.clean_existing:
        parser.error("give a CSV path, or --clean-existing")
    if args.csv_path and not args.csv_path.is_file():
        print(f"File not found: {args.csv_path}", file=sys.stderr)
        return 1
    db.init_db()
    with db.connect() as conn:
        if args.csv_path:
            print(ingest_csv(conn, args.csv_path))
            print("All new passages are Pending and not retrievable until validated.")
        if args.clean_existing:
            print(clean_existing(conn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
