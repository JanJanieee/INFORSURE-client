"""Turn per-passage NLI probabilities into one evidence verdict (thesis section 5). Pure logic."""
import numpy as np

from ..schemas import EvidenceLabel


def aggregate(probs: np.ndarray, min_confidence: float) -> EvidenceLabel:
    """probs: (n_passages, 3) as [entailment, neutral, contradiction].

    Supported needs a passage that entails the claim with >= `min_confidence` and no passage that contradicts
    it with >= `min_confidence` (and vice versa). If passages disagree strongly, or nothing is confident,
    the result is Insufficient Evidence, never a guess.
    """
    if len(probs) == 0:
        return EvidenceLabel.INSUFFICIENT
    entail, contra = float(probs[:, 0].max()), float(probs[:, 2].max())
    if entail >= min_confidence and contra < min_confidence:
        return EvidenceLabel.SUPPORTED
    if contra >= min_confidence and entail < min_confidence:
        return EvidenceLabel.CONTRADICTED
    return EvidenceLabel.INSUFFICIENT
