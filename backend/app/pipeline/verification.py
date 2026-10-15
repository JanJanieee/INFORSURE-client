"""Buuin ang evidence verdict mula sa NLI scores ng passages."""
import numpy as np

from ..schemas import EvidenceLabel


def aggregate(probs: np.ndarray, min_confidence: float) -> EvidenceLabel:
    """Buuin ang verdict; kulang o conflicting evidence ay Insufficient."""
    if len(probs) == 0:
        return EvidenceLabel.INSUFFICIENT
    entail, contra = float(probs[:, 0].max()), float(probs[:, 2].max())
    if entail >= min_confidence and contra < min_confidence:
        return EvidenceLabel.SUPPORTED
    if contra >= min_confidence and entail < min_confidence:
        return EvidenceLabel.CONTRADICTED
    return EvidenceLabel.INSUFFICIENT
