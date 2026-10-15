"""Ihanda ang client assets at runtime DB; panatilihin ang existing feedback."""
import argparse
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

import numpy as np

from . import config
from .pipeline import evidence_index, lexicon
from .pipeline.model_store import load_model, read_metadata, required_artifacts

ACTIVE_MODEL = config.ROOT / "models" / "active.json"
DEMO_VERSION = os.environ.get("INFOSURE_MODEL_VERSION") or (
    json.loads(ACTIVE_MODEL.read_text(encoding="utf-8"))["model_version"] if ACTIVE_MODEL.is_file() else "v0.2-xlmr-pubhealth-en-exp"
)
SOURCE_DB = config.ROOT / "data" / "infosure.db"


# Buksan ang DB for read-only access; isara pagkatapos.
@contextmanager
def readonly(path: Path):
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# I-check ang DB, model registration at matching evidence index.
def check_database(path: Path) -> int:
    with readonly(path) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError(f"Database integrity check failed: {path}")
        row = conn.execute(
            "SELECT model_version FROM model_versions WHERE model_version = ?", (DEMO_VERSION,)
        ).fetchone()
        if row is None:
            raise ValueError("The demo model is not registered; feedback would fail.")
        state = evidence_index.status(conn)
    if not state["validated"] or not state["built"] or state["stale"]:
        raise ValueError(f"Evidence index is missing, empty, or stale for {path}: {state}")
    vectors = np.load(config.INDEX_DIR / "vectors.npy", allow_pickle=False)
    if vectors.ndim != 2 or vectors.shape[0] != state["indexed"] or not np.isfinite(vectors).all():
        raise ValueError("Evidence vectors are incomplete or invalid.")
    return state["validated"]


# I-check ang model, lexicon, DB at matching evidence index.
def check_assets() -> int:
    model_directory = config.MODELS_DIR / DEMO_VERSION
    metadata = read_metadata(str(model_directory))
    required = [
        SOURCE_DB,
        model_directory / "metadata.json",
        *[model_directory / name for name in required_artifacts(metadata)],
        config.INDEX_DIR / "index.json",
        config.INDEX_DIR / "vectors.npy",
        config.LEXICON_PATH,
        config.ROOT / "extension" / "manifest.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Missing shipped assets: " + ", ".join(missing))
    count = check_database(SOURCE_DB)
    lexicon.reload_lexicon()
    if not lexicon.is_health_text("Smoking increases the risk of lung cancer."):
        raise ValueError("The health lexicon could not recognize the demo claim.")
    os.environ["INFOSURE_MODEL_VERSION"] = DEMO_VERSION
    classifier = load_model()
    label, confidence = classifier.predict("Smoking increases the risk of lung cancer.")
    if label not in ("Reliable", "Misinformation") or not 0 <= confidence <= 1:
        raise ValueError("The shipped classifier returned an invalid prediction.")
    print(f"Assets OK: {count} validated passages; matching index; lexicon; {DEMO_VERSION} classifier.")
    gate = metadata.get("acceptance_gate", {})
    if not gate.get("min_macro_f1") and not gate.get("min_per_class_recall"):
        print("Development model: its acceptance gate was disabled.")
    elif metadata.get("gate_passed") is False:
        print("DEVELOPMENT PREVIEW: this candidate failed its acceptance gate; it is not Deployed.")
    return count


# Ihanda ang runtime DB nang hindi binubura ang feedback.
def prepare_runtime() -> Path:
    check_assets()
    runtime = Path(os.environ.get("INFOSURE_DB", config.ROOT / "data" / "runtime" / "infosure.db"))
    if runtime.resolve() == SOURCE_DB.resolve():
        raise ValueError("Use data/runtime/infosure.db for the demo, keeping the shipped DB as a snapshot.")
    runtime.parent.mkdir(parents=True, exist_ok=True)
    if not runtime.exists():
        # SQLite backup kahit bukas sa ibang process ang source DB.
        with readonly(SOURCE_DB) as source, closing(sqlite3.connect(runtime)) as target:
            source.backup(target)
        print(f"Created demo runtime database: {runtime}")
    config.DB_PATH = runtime
    # Idagdag ang model registration; panatilihin ang existing feedback.
    from . import db

    with readonly(SOURCE_DB) as source, closing(db.connect(runtime)) as target, target:
        selected = source.execute("SELECT * FROM model_versions WHERE model_version = ?", (DEMO_VERSION,)).fetchone()
        dataset_version = selected["dataset_version"]
        if dataset_version:
            dataset = source.execute("SELECT * FROM dataset_versions WHERE dataset_version = ?", (dataset_version,)).fetchone()
            target.execute(
                "INSERT OR IGNORE INTO dataset_versions (dataset_version, description, sample_count, artifact_path) VALUES (?, ?, ?, ?)",
                (dataset_version, dataset["description"], dataset["sample_count"], dataset["artifact_path"]),
            )
        target.execute(
            "INSERT OR IGNORE INTO model_versions (model_version, dataset_version, metrics_json, artifact_path, deployment_status, trained_at) "
            "VALUES (?, ?, ?, ?, 'Candidate', ?)",
            (DEMO_VERSION, dataset_version, selected["metrics_json"], str(config.MODELS_DIR / DEMO_VERSION), selected["trained_at"]),
        )
    check_database(runtime)
    print(f"Runtime DB OK: {runtime}")
    return runtime


# I-load ang retrieval, NLI at OCR bago gamitin.
def warm_models() -> None:
    from . import ocr
    from .pipeline import embeddings, nli

    print("Loading embedding model (first setup downloads it)...", flush=True)
    embeddings.embed(["warm up"])
    print("Loading NLI verifier (first setup downloads it)...", flush=True)
    nli.predict(["warm up passage"], ["warm up claim"])
    print("Loading OCR assets...", flush=True)
    ocr.get_engine()
    print("Embedding, NLI, classifier, and OCR are ready.")


# Patakbuhin ang asset check, preparation o warmup command.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "prepare", "warmup"))
    command = parser.parse_args(argv).command
    try:
        if command == "check":
            check_assets()
        else:
            prepare_runtime()
            if command == "warmup":
                warm_models()
    except Exception as exc:
        print(f"Demo check failed: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
