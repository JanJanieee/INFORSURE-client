"""Shared prediction helper para sa fitted SVM/NB pipelines."""
import numpy as np


def predict_with_confidence(pipe, texts) -> tuple[list[str], list[float]]:
    """Kunin ang labels; NB probability o SVM margin ang confidence."""
    clf = pipe.named_steps["clf"]
    labels = list(pipe.predict(texts))
    if hasattr(clf, "predict_proba"):
        confidence = pipe.predict_proba(texts).max(axis=1)
    else:
        margin = np.abs(pipe.decision_function(texts))
        confidence = 1.0 / (1.0 + np.exp(-margin))
    return labels, [float(value) for value in confidence]
