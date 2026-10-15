"""Partition SHAP para sa mismong transformer; walang surrogate o training."""
import logging
from threading import BoundedSemaphore

import numpy as np

from .. import config
from ..schemas import ExplainResponse, TokenAttribution

logger = logging.getLogger(__name__)
SLOT = BoundedSemaphore(1)


class ExplanationUnavailable(RuntimeError):
    pass


class PredictionChanged(ValueError):
    pass


class LimitedTokenizer:
    # Gamitin ang parehong truncation limit ng live classifier.
    def __init__(self, tokenizer, max_length):
        self.tokenizer = tokenizer
        self.max_length = max_length

    # Ipasa ang tokenizer attributes na kailangan ng SHAP.
    def __getattr__(self, name):
        return getattr(self.tokenizer, name)

    # I-mask lang ang tokens na talagang nakita ng classifier.
    def __call__(self, text, **kwargs):
        encoded = self.tokenizer(text, **{
            **kwargs, "truncation": True, "max_length": self.max_length, "return_offsets_mapping": True,
        })
        positions = [i for i, (start, end) in enumerate(encoded["offset_mapping"]) if end > start]
        return {key: [encoded[key][i] for i in positions] for key in ("input_ids", "offset_mapping")}


# Ihambing ang SHAP total sa tunay na prediction bago ipakita.
def explain(classifier, claim: str, expected_label: str) -> ExplainResponse:
    try:
        import shap
    except ImportError as exc:
        raise ExplanationUnavailable("Install the updated backend requirements to enable SHAP.") from exc

    label, confidence = classifier.predict(claim)
    if label != expected_label:
        raise PredictionChanged("The prediction changed. Check the claim again before explaining it.")
    if classifier.tokenizer.mask_token_id is None or not classifier.tokenizer.is_fast:
        raise ExplanationUnavailable("This classifier needs a fast tokenizer with a mask token for SHAP.")

    tokenizer = LimitedTokenizer(classifier.tokenizer, classifier.max_length)
    encoded = classifier.tokenizer(claim, truncation=True, max_length=classifier.max_length, return_offsets_mapping=True)
    positions = [i for i, (start, end) in enumerate(encoded["offset_mapping"]) if end > start]
    if not positions:
        raise ExplanationUnavailable("No text tokens are available to explain.")
    offsets = encoded["offset_mapping"]
    max_evals = max(16, min(512, config.SHAP_MAX_EVALS))
    batch_size = max(1, min(8, config.SHAP_BATCH_SIZE))
    # Parehong haba at positions; mask tokens ang kapalit ng hidden words.
    masker = shap.maskers.Text(tokenizer, collapse_mask_token=False, output_type="token_ids")
    if len(positions) == 1:
        masker.clustering = np.empty((0, 4))

    # Fixed ang boundary tokens; content tokens lang ang SHAP features.
    def masked_probabilities(masked_tokens):
        batch = np.tile(encoded["input_ids"], (len(masked_tokens), 1))
        batch[:, positions] = masked_tokens
        return classifier.token_probabilities(batch)

    explainer = shap.PartitionExplainer(masked_probabilities, masker, output_names=classifier.labels)
    result = explainer([claim], max_evals=max_evals, batch_size=batch_size, silent=True)
    index = classifier.labels.index(label)
    values = np.asarray(result.values[0, :, index], dtype=float)
    base = float(result.base_values[0, index])
    if len(values) != len(positions) or not np.isfinite(values).all() or not np.isfinite(base):
        raise ExplanationUnavailable("SHAP returned invalid token contributions.")
    total = float(values.sum())
    if abs(base + total - confidence) > 1e-4:
        logger.warning("SHAP did not reproduce the classifier score for model %s", classifier.version)
        raise ExplanationUnavailable("The explanation did not match the prediction. Please try again.")

    attributions = []
    for value, position in zip(values, positions):
        start, end = offsets[position]
        attributions.append(TokenAttribution(text=claim[start:end], start=start, end=end, value=float(value)))
    explained_end = max((end for start, end in offsets if end > start), default=0)
    full_length = len(classifier.tokenizer(claim, truncation=False)["input_ids"])
    return ExplainResponse(
        claim=claim, model_version=classifier.version, ml_label=label,
        base_value=base, output_value=confidence, attribution_sum=total, attributions=attributions,
        input_truncated=full_length > classifier.max_length, explained_characters=explained_end,
        max_evals=max_evals,
    )
