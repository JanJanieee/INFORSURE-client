# Dito ang SQLite connections, tables at DB updates.
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterator

from . import config

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


# Buksan ang SQLite DB na may foreign-key checks.
def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Idagdag ang columns na wala pa sa lumang DB.
_ADDED_COLUMNS = {"evidence": [("reviewed_by", "TEXT"), ("reviewed_at", "TEXT"), ("license_note", "TEXT"), ("review_note", "TEXT")]}


# Idagdag ang kulang na columns sa lumang DB.
def _migrate(conn: sqlite3.Connection) -> None:
    for table, columns in _ADDED_COLUMNS.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


# Ihanda ang DB tables at supported updates.
def init_db(path: Path | str | None = None) -> None:
    db_path = Path(path or config.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as conn, conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(conn)


def get_conn() -> Iterator[sqlite3.Connection]:
    """Magbigay ng DB connection; isara pagkatapos ng request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
