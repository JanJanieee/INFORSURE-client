"""Prepare and verify the shipped demo without training or changing its source DB.

Run from the repository root: py -m backend.app.handoff check|prepare|warmup|smoke
"""
import argparse
import io
import os
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

import numpy as np

from . import config
from .pipeline import evidence_index, lexicon
from .pipeline.model_store import load_model

DEMO_VERSION = "v0.0-dev"
SOURCE_DB = config.ROOT / "data" / "infosure.db"


@contextmanager
def readonly(path: Path):
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


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


def check_assets() -> int:
    required = [
        SOURCE_DB,
        config.MODELS_DIR / DEMO_VERSION / "model.joblib",
        config.MODELS_DIR / DEMO_VERSION / "metadata.json",
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
    print("Using the existing dev classifier for a demo; its acceptance gate was disabled.")
    return count


def prepare_runtime() -> Path:
    check_assets()
    runtime = Path(os.environ.get("INFOSURE_DB", config.ROOT / "data" / "runtime" / "infosure.db"))
    if runtime.resolve() == SOURCE_DB.resolve():
        raise ValueError("Use data/runtime/infosure.db for the demo, keeping the shipped DB as a snapshot.")
    runtime.parent.mkdir(parents=True, exist_ok=True)
    if not runtime.exists():
        # SQLite backup also works when another process has the source database open.
        with readonly(SOURCE_DB) as source, closing(sqlite3.connect(runtime)) as target:
            source.backup(target)
        print(f"Created demo runtime database: {runtime}")
    config.DB_PATH = runtime
    check_database(runtime)
    print(f"Runtime DB OK: {runtime}")
    return runtime


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


def smoke() -> None:
    """Use real models and a disposable DB to check both API input paths and feedback."""
    from fastapi.testclient import TestClient
    from PIL import Image, ImageDraw, ImageFont

    from .main import app

    def checked(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    original_db, original_warmup = config.DB_PATH, config.WARMUP
    with tempfile.TemporaryDirectory(prefix="infosure-smoke-") as folder:
        isolated = Path(folder) / "smoke.db"
        with readonly(original_db) as source, closing(sqlite3.connect(isolated)) as target:
            source.backup(target)
        config.DB_PATH, config.WARMUP = isolated, False
        try:
            with TestClient(app) as client:
                for text, scope in [
                    ("The team won the championship game last night.", "out_of_scope"),
                    ("Does smoking cause cancer?", "no_verifiable_health_claim"),
                    ("I think vaccines are scary.", "no_verifiable_health_claim"),
                ]:
                    response = client.post("/analyze", json={"text": text})
                    checked(response.status_code == 200, response.text)
                    checked(response.json()["scope"] == scope, f"Scope check failed: {text}")
                print("Scope checks OK: non-health, question, opinion.", flush=True)

                claim = "Smoking increases the risk of lung cancer."
                for source in ("text", "image"):
                    text = claim
                    if source == "image":
                        image = Image.new("RGB", (1200, 160), "white")
                        ImageDraw.Draw(image).text((30, 45), claim, font=ImageFont.load_default(size=42), fill="black")
                        buffer = io.BytesIO()
                        image.save(buffer, format="PNG")
                        response = client.post("/ocr", files={"file": ("claim.png", buffer.getvalue(), "image/png")})
                        checked(response.status_code == 200, response.text)
                        text = response.json()["text"]
                        checked("cancer" in text.lower(), f"OCR did not read the claim: {text!r}")
                    response = client.post("/analyze", json={"text": text, "source": source})
                    checked(response.status_code == 200, response.text)
                    body = response.json()
                    checked(body["scope"] == "verified", f"{source}: claim did not reach classification")
                    checked(body["model_version"] == DEMO_VERSION, "Wrong classifier version")
                    checked(bool(body["evidence"]), f"{source}: no evidence was retrieved")
                    checked(all(e["relation"] and e["source_url"] for e in body["evidence"]), "Missing NLI scores/sources")
                    checked(bool(body["assessment"]), "Missing final assessment")
                    print(f"{source} flow OK: {body['ml_label']}; {body['evidence_result']}; {len(body['evidence'])} sources.", flush=True)
                response = client.post("/feedback", json={
                    "claim_text": body["claim"], "model_prediction": body["ml_label"],
                    "model_confidence": body["ml_confidence"], "evidence_result": body["evidence_result"],
                    "model_version": DEMO_VERSION, "user_feedback": "Agree",
                })
                checked(response.status_code == 201, response.text)
                print("Feedback OK (written only to a disposable test database).")
        finally:
            config.DB_PATH, config.WARMUP = original_db, original_warmup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "prepare", "warmup", "smoke"))
    command = parser.parse_args(argv).command
    try:
        if command == "check":
            check_assets()
        else:
            prepare_runtime()
            if command == "warmup":
                warm_models()
            elif command == "smoke":
                smoke()
    except Exception as exc:
        print(f"Demo check failed: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
