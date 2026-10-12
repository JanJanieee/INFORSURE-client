"""Vector index over VALIDATED evidence only (thesis sections 5 and 8).

SQLite stays the source of metadata; vectors live in `data/index/` (vectors.npy + index.json).
The index records a hash of the validated (id, text) rows it was built from. If the validated set
changes (new approval, rejection, edit) the index is stale and retrieval refuses to run rather than
return rejected or missing evidence. Rebuild with `py -m backend.app.review index build`.
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .. import config
from ..schemas import EvidenceItem
from . import embeddings


class EvidenceIndexStale(RuntimeError):
    pass


def _paths() -> tuple[Path, Path]:
    return config.INDEX_DIR / "vectors.npy", config.INDEX_DIR / "index.json"


def _validated_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT evidence_id, evidence_text FROM validated_evidence ORDER BY evidence_id").fetchall()


def content_hash(rows) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(f"{r['evidence_id']}\t{r['evidence_text']}\n".encode("utf-8"))
    return h.hexdigest()


def build_index(conn: sqlite3.Connection) -> dict:
    """Embed every Validated passage, save the index atomically, and record embedding_reference."""
    rows = _validated_rows(conn)
    vec_path, meta_path = _paths()
    vec_path.parent.mkdir(parents=True, exist_ok=True)
    vectors = embeddings.embed([r["evidence_text"] for r in rows]) if rows else np.zeros((0, 0), np.float32)
    meta = {
        "embedding_model": config.EMBEDDING_MODEL,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ids": [r["evidence_id"] for r in rows],
        "content_hash": content_hash(rows),
        "dim": int(vectors.shape[1]) if rows else 0,
    }
    # np.save appends ".npy" to names that lack it, so the temp name must already end in ".npy".
    tmp_vec, tmp_meta = vec_path.with_name("vectors.tmp.npy"), meta_path.with_suffix(".json.tmp")
    np.save(tmp_vec, vectors)
    tmp_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    os.replace(tmp_vec, vec_path)
    os.replace(tmp_meta, meta_path)

    with conn:
        conn.execute("UPDATE evidence SET embedding_reference = NULL WHERE embedding_reference IS NOT NULL")
        conn.executemany(
            "UPDATE evidence SET embedding_reference = ? WHERE evidence_id = ?",
            [(f"{config.EMBEDDING_MODEL}#{i}", eid) for i, eid in enumerate(meta["ids"])],
        )
    return meta


def status(conn: sqlite3.Connection) -> dict:
    rows = _validated_rows(conn)
    _, meta_path = _paths()
    if not meta_path.is_file():
        return {"validated": len(rows), "indexed": 0, "built": False, "stale": bool(rows)}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    stale = meta["content_hash"] != content_hash(rows) or meta["embedding_model"] != config.EMBEDDING_MODEL
    return {"validated": len(rows), "indexed": len(meta["ids"]), "built": True, "stale": stale,
            "built_at": meta["built_at"], "embedding_model": meta["embedding_model"]}


def search(conn: sqlite3.Connection, claim: str) -> list[EvidenceItem]:
    """Top-k validated passages above SIMILARITY_MIN. Empty list means no relevant evidence."""
    st = status(conn)
    if st["validated"] == 0:
        return []
    if not st["built"] or st["stale"]:
        raise EvidenceIndexStale(
            "Evidence index is missing or out of date. Run: py -m backend.app.review index build"
        )
    vec_path, meta_path = _paths()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    vectors = np.load(vec_path)
    scores = vectors @ embeddings.embed([claim])[0]
    order = np.argsort(-scores)[: config.RETRIEVAL_TOP_K]
    hits = [(meta["ids"][i], float(scores[i])) for i in order if scores[i] >= config.SIMILARITY_MIN]
    items = []
    for evidence_id, similarity in hits:
        r = conn.execute(
            "SELECT evidence_id, evidence_text, source_name, source_url, publication_date "
            "FROM validated_evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if r is not None:
            items.append(EvidenceItem(similarity=similarity, **dict(r)))
    return items
