"""Evaluation and acceptance gate (thesis section 13.7)."""
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

LABELS = ["Reliable", "Misinformation"]
MAX_ERROR_EXAMPLES = 10


def evaluate(y_true: list[str], y_pred: list[str], texts: list[str]) -> dict:
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    per_class = {
        label: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
        for label, p, r, f, s in zip(LABELS, prec, rec, f1, support)
    }
    errors = {"false_positives": [], "false_negatives": []}  # positive class = Misinformation
    for t, true, pred in zip(texts, y_true, y_pred):
        if pred == "Misinformation" and true == "Reliable":
            errors["false_positives"].append(t)
        elif pred == "Reliable" and true == "Misinformation":
            errors["false_negatives"].append(t)
    errors = {k: v[:MAX_ERROR_EXAMPLES] for k, v in errors.items()}
    return {
        "n": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(sum(prec) / len(prec)),
        "macro_recall": float(sum(rec) / len(rec)),
        "macro_f1": float(sum(f1) / len(f1)),
        "per_class": per_class,
        "confusion_matrix": {"labels": LABELS, "matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist()},
        "error_examples": errors,
    }


def check_gate(metrics: dict, gate: dict) -> tuple[bool, list[str]]:
    """Predefined acceptance criteria. Deployment requires passed == True."""
    failures = []
    if metrics["macro_f1"] < gate["min_macro_f1"]:
        failures.append(f"macro_f1 {metrics['macro_f1']:.3f} < {gate['min_macro_f1']}")
    for label, m in metrics["per_class"].items():
        if m["recall"] < gate["min_per_class_recall"]:
            failures.append(f"recall[{label}] {m['recall']:.3f} < {gate['min_per_class_recall']}")
    return not failures, failures
