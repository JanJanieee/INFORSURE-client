"""Load a packaged claim classifier locally, without importing training code."""
import math
from pathlib import Path


class TransformerClassifier:
    def __init__(self, directory: Path, metadata: dict, version: str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.version = version
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_length = int(metadata.get("inference", {}).get("max_length", 128))
        self.temperature = float((directory / "temperature.txt").read_text(encoding="utf-8"))
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("Classifier temperature must be a positive finite number")
        self.tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(directory, local_files_only=True).eval()
        self.model.to(self.device)
        self.labels = [self.model.config.id2label[i] for i in range(self.model.config.num_labels)]
        if set(self.labels) != {"Reliable", "Misinformation"}:
            raise ValueError(f"Classifier labels are invalid: {self.labels}")
        if self.max_length < 1:
            raise ValueError("Classifier max_length must be positive")

    def predict(self, claim: str) -> tuple[str, float]:
        import torch

        encoded = self.tokenizer(
            [claim], truncation=True, max_length=self.max_length, padding=True, return_tensors="pt"
        ).to(self.device)
        with torch.inference_mode():
            logits = self.model(**encoded).logits.float() / self.temperature
            probabilities = torch.softmax(logits, dim=-1)[0]
        best = int(probabilities.argmax().item())
        return self.labels[best], float(probabilities[best].item())
