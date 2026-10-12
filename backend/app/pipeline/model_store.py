"""Load the classifier artifact packaged by training/package.py (thesis section 13.8).

Resolution order for the model version:
1. env INFOSURE_MODEL_VERSION (explicit override, e.g. a dev model while testing)
2. the single model whose deployment_status is 'Deployed' in `model_versions`
A Candidate is never used implicitly: deploying is a deliberate step after the acceptance gate
(`py -m backend.app.deploy`).

Every artifact is wrapped in a `Classifier` with one method, `predict(claim) -> (label, confidence)`, chosen by
`model_type` in metadata.json. The pipeline only sees that interface, so a new model type (e.g. a transformer) is
added here without touching the pipeline.
"""
import json
import os
from contextlib import closing
from functools import lru_cache
from typing import Protocol

import joblib

from .. import config, db
from .prediction import predict_with_confidence


class ModelNotAvailable(RuntimeError):
    pass


class Classifier(Protocol):
    version: str

    def predict(self, claim: str) -> tuple[str, float]:
        """Return (label, confidence). Labels are 'Reliable' or 'Misinformation'."""


class SklearnClassifier:
    """Linear SVM or Naive Bayes pipeline (TF-IDF + estimator) saved with joblib."""

    def __init__(self, pipeline, version: str):
        self.pipeline = pipeline
        self.version = version

    def predict(self, claim: str) -> tuple[str, float]:
        labels, confidences = predict_with_confidence(self.pipeline, [claim])
        return labels[0], confidences[0]


def _load_sklearn(model_dir: str, version: str) -> Classifier:
    model_path = os.path.join(model_dir, "model.joblib")
    if not os.path.isfile(model_path):
        raise ModelNotAvailable(f"Model artifact not found: {model_path}")
    return SklearnClassifier(joblib.load(model_path), version)


# model_type in metadata.json -> loader. Add "transformer" here once that stage exists.
LOADERS = {"svm": _load_sklearn, "nb": _load_sklearn}
SUPPORTED_TYPES = tuple(LOADERS)


def read_metadata(model_dir: str) -> dict:
    path = os.path.join(model_dir, "metadata.json")
    if not os.path.isfile(path):
        raise ModelNotAvailable(f"Model metadata not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_supported(metadata: dict) -> str:
    model_type = metadata.get("model_type", "svm")
    if model_type not in LOADERS:
        raise ModelNotAvailable(f"Unsupported model type '{model_type}' (supported: {', '.join(SUPPORTED_TYPES)}).")
    return model_type


def resolve_version() -> str:
    explicit = os.environ.get("INFOSURE_MODEL_VERSION")
    if explicit:
        return explicit
    db.init_db()
    with closing(db.connect()) as conn:
        row = conn.execute(
            "SELECT model_version FROM model_versions WHERE deployment_status = 'Deployed'"
        ).fetchone()
    if row is None:
        raise ModelNotAvailable(
            "No deployed model. Deploy a gated model with `py -m backend.app.deploy deploy VERSION`, "
            "or set INFOSURE_MODEL_VERSION for development."
        )
    return row[0]


@lru_cache(maxsize=4)
def _load(models_dir: str, version: str) -> tuple[Classifier, dict]:
    model_dir = os.path.join(models_dir, version)
    metadata = read_metadata(model_dir)
    return LOADERS[check_supported(metadata)](model_dir, version), metadata


def load_model() -> Classifier:
    classifier, _metadata = _load(str(config.MODELS_DIR), resolve_version())
    return classifier
