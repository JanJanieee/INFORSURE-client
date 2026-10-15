"""Transformer candidate (thesis section 13.5): xlm-roberta-base fine-tuned as the claim classifier.

Settings live in configs under "transformer", sized for a 4 GB GPU (RTX 2050): fp16, batch size 8,
max length 128, gradient accumulation 4. Lower the batch size on out-of-memory.

Text stays as natural sentences, with negation (section 13.4). The best epoch is chosen on VALIDATION
macro-F1. Raw softmax scores are over-confident, so one temperature is fitted on validation logits; the
result is a probability that can be blended with the calibrated SVM/NB scores (section 13.6).

Used by the training pipeline and experiments; saved artifacts also load in the backend.
"""
import time
import math
from pathlib import Path

import numpy as np
import pandas as pd

PROGRESS_EVERY = 5  # print every this many optimizer steps
POSITIVE = "Misinformation"
LABELS = ["Reliable", "Misinformation"]  # index 0 / 1


def _require_torch():
    try:
        import torch
        import transformers
    except ImportError as exc:
        raise RuntimeError("Transformer stage needs torch and transformers (CUDA build of torch for the GPU).") from exc
    return torch, transformers


class TransformerClassifier:
    """Fine-tuned sequence classifier with a validation-fitted temperature."""

    def __init__(self, model, tokenizer, max_length: int, temperature: float, device: str):
        self.model, self.tokenizer = model, tokenizer
        self.max_length, self.temperature, self.device = max_length, temperature, device

    def logits(self, texts, batch_size: int = 32) -> np.ndarray:
        torch, _ = _require_torch()
        self.model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                enc = self.tokenizer(list(texts[i:i + batch_size]), truncation=True, max_length=self.max_length,
                                     padding=True, return_tensors="pt").to(self.device)
                with torch.autocast(device_type=self.device, enabled=self.device == "cuda"):
                    out.append(self.model(**enc).logits.float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, len(LABELS)), dtype=np.float32)

    def p_positive(self, texts) -> np.ndarray:
        z = self.logits(list(texts)) / self.temperature
        z = z - z.max(axis=1, keepdims=True)
        p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
        return p[:, LABELS.index(POSITIVE)]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.model.config.id2label = dict(enumerate(LABELS))
        self.model.config.label2id = {label: i for i, label in enumerate(LABELS)}
        self.model.save_pretrained(directory, safe_serialization=True)
        self.tokenizer.save_pretrained(directory)
        (directory / "temperature.txt").write_text(str(self.temperature), encoding="utf-8")


def _fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """Single-parameter temperature scaling on validation logits (minimise log-loss)."""
    best_t, best_loss = 1.0, float("inf")
    for t in np.arange(0.5, 5.01, 0.05):
        z = logits / t
        z = z - z.max(axis=1, keepdims=True)
        logp = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        loss = -logp[np.arange(len(y)), y].mean()
        if loss < best_loss:
            best_t, best_loss = float(t), float(loss)
    return best_t


def _macro_f1(y: np.ndarray, pred: np.ndarray) -> float:
    f1 = []
    for c in (0, 1):
        tp = int(((pred == c) & (y == c)).sum())
        fp = int(((pred == c) & (y != c)).sum())
        fn = int(((pred != c) & (y == c)).sum())
        f1.append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0)
    return sum(f1) / 2


def train_transformer(train_df: pd.DataFrame, val_df: pd.DataFrame, cfg: dict, save_dir: Path | None = None):
    """Fine-tune on train, pick the epoch on validation, return a TransformerClassifier.

    If `save_dir` already holds a saved model, it is loaded instead of retrained.
    """
    torch, transformers = _require_torch()
    t = cfg["transformer"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])

    if save_dir and (save_dir / "temperature.txt").exists():
        tok = transformers.AutoTokenizer.from_pretrained(save_dir)
        model = transformers.AutoModelForSequenceClassification.from_pretrained(save_dir).to(device)
        return TransformerClassifier(model, tok, t["max_length"], float((save_dir / "temperature.txt").read_text()), device)

    tok = transformers.AutoTokenizer.from_pretrained(t["model_name"])
    model = transformers.AutoModelForSequenceClassification.from_pretrained(t["model_name"], num_labels=2).to(device)
    model.config.id2label = dict(enumerate(LABELS))
    model.config.label2id = {label: i for i, label in enumerate(LABELS)}
    ytr = np.array([LABELS.index(x) for x in train_df["label"]])
    yva = np.array([LABELS.index(x) for x in val_df["label"]])
    texts = list(train_df["text"])

    counts = np.bincount(ytr, minlength=2)
    weights = torch.tensor(len(ytr) / (2 * counts), dtype=torch.float, device=device)  # balanced, like the SVM
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    opt = torch.optim.AdamW(model.parameters(), lr=t["learning_rate"], weight_decay=0.01)
    batches_per_epoch = math.ceil(len(texts) / t["batch_size"])
    steps = math.ceil(batches_per_epoch / t["grad_accum_steps"]) * t["epochs"]
    sched = transformers.get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda" and t["fp16"])

    clf = TransformerClassifier(model, tok, t["max_length"], 1.0, device)
    best_f1, best_state = -1.0, None
    started, running = time.time(), []
    eval_batch_size = t.get("eval_batch_size", t["batch_size"])
    opt.zero_grad(set_to_none=True)
    for epoch in range(t["epochs"]):
        model.train()
        order = np.random.permutation(len(texts))
        for k, i in enumerate(range(0, len(order), t["batch_size"])):
            idx = order[i:i + t["batch_size"]]
            enc = tok([texts[j] for j in idx], truncation=True, max_length=t["max_length"], padding=True,
                      return_tensors="pt").to(device)
            with torch.autocast(device_type=device, enabled=device == "cuda" and t["fp16"]):
                logits = model(**enc).logits
            accumulation_size = min(t["grad_accum_steps"], batches_per_epoch - (k // t["grad_accum_steps"]) * t["grad_accum_steps"])
            loss = loss_fn(logits.float(), torch.tensor(ytr[idx], device=device)) / accumulation_size
            scaler.scale(loss).backward()
            running.append(loss.item() * accumulation_size)
            if (k + 1) % (t["grad_accum_steps"] * PROGRESS_EVERY) == 0:
                print(f"    epoch {epoch + 1}/{t['epochs']} {100 * (k + 1) / batches_per_epoch:5.1f}%  "
                      f"loss {np.mean(running):.3f}  {(time.time() - started) / 60:.1f} min", flush=True)
                running = []
            if (k + 1) % t["grad_accum_steps"] == 0 or k + 1 == batches_per_epoch:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt)
                scaler.update()
                sched.step()
                opt.zero_grad(set_to_none=True)
        f1 = _macro_f1(yva, clf.logits(list(val_df["text"]), batch_size=eval_batch_size).argmax(axis=1))
        print(f"  xlm-roberta epoch {epoch + 1}/{t['epochs']}: val macro_f1={f1:.3f}", flush=True)
        if f1 > best_f1:
            best_f1 = f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    clf.temperature = _fit_temperature(clf.logits(list(val_df["text"]), batch_size=eval_batch_size), yva)
    if save_dir:
        clf.save(save_dir)
    return clf
