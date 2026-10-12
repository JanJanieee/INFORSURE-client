"""Natural-language-inference scoring for evidence verification (thesis section 5).

premise = evidence passage, hypothesis = claim. Returns probabilities in the fixed order
[entailment, neutral, contradiction]. Tests replace `predict` with a fake instead of loading the model.
"""
from functools import lru_cache

import numpy as np

from .. import config

ORDER = ("entailment", "neutral", "contradiction")
MAX_LENGTH = 256


@lru_cache(maxsize=1)
def _load():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(config.NLI_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(config.NLI_MODEL).eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    labels = {i: name.lower() for i, name in model.config.id2label.items()}
    missing = set(ORDER) - set(labels.values())
    if missing:
        raise RuntimeError(f"NLI model lacks labels {sorted(missing)}; found {sorted(labels.values())}")
    column = [next(i for i, n in labels.items() if n == name) for name in ORDER]
    return tokenizer, model, device, column


def predict(premises: list[str], hypotheses: list[str], batch_size: int = 16) -> np.ndarray:
    import torch

    tokenizer, model, device, column = _load()
    out = []
    for start in range(0, len(premises), batch_size):
        batch = tokenizer(
            premises[start:start + batch_size], hypotheses[start:start + batch_size],
            truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt",
        ).to(device)
        with torch.inference_mode(), torch.autocast(device_type=device, dtype=torch.float16, enabled=device == "cuda"):
            logits = model(**batch).logits.float()
        out.append(torch.softmax(logits, dim=-1).cpu().numpy()[:, column])
    return np.concatenate(out) if out else np.zeros((0, 3), np.float32)
