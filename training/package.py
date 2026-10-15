"""Model packaging and registration (thesis section 13.8, 14.2).

Writes models/<version>/ and registers it in `model_versions` as Candidate. Deploying
(status Deployed) is a separate, deliberate step.
"""
import hashlib
import json
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy
import pandas
import sklearn

from backend.app import db
from training.evaluate import LABELS, check_gate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_model(
    pipeline,
    *,
    version: str,
    model_type: str,
    cfg: dict,
    metrics: dict,
    dataset_path: Path,
    dataset_version: str,
    models_dir: Path,
    db_path: Path | None = None,
) -> Path:
    out = models_dir / version
    if out.exists():
        raise FileExistsError(f"{out} already exists; pick a new version")
    out.mkdir(parents=True)

    if model_type == "transformer":
        pipeline.save(out)
    else:
        joblib.dump(pipeline, out / "model.joblib")  # includes the fitted vectorizer
    trained_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata = {
        "model_version": version,
        "model_type": model_type,
        "labels": LABELS,
        "label_map": {label: i for i, label in enumerate(LABELS)},
        "training_date": trained_at,
        "dataset_version": dataset_version,
        "dataset_sha256": _sha256(dataset_path),
        "acceptance_gate": cfg["acceptance_gate"],
        "gate_passed": check_gate(metrics, cfg["acceptance_gate"])[0],
        "config": cfg,
        "metrics": metrics,
        "libraries": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "pandas": pandas.__version__,
            "numpy": numpy.__version__,
        },
    }
    if model_type == "transformer":
        import torch
        import transformers

        metadata["inference"] = {"max_length": pipeline.max_length, "temperature": pipeline.temperature}
        metadata["training_language"] = cfg.get("training_language")
        metadata["libraries"].update(torch=torch.__version__, transformers=transformers.__version__)
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    db.init_db(db_path)
    with db.connect(db_path) as conn:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO dataset_versions (dataset_version, artifact_path) VALUES (?, ?)",
                (dataset_version, str(dataset_path)),
            )
            conn.execute(
                "INSERT INTO model_versions (model_version, dataset_version, metrics_json, artifact_path, "
                "deployment_status, trained_at) VALUES (?, ?, ?, ?, 'Candidate', ?)",
                (version, dataset_version, json.dumps(metrics), str(out), trained_at),
            )
        except sqlite3.IntegrityError as exc:
            raise RuntimeError(f"model version '{version}' is already registered") from exc
    return out
