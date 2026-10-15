"""Pagsamahin ang model estimate at evidence verdict sa assessment."""
from ..schemas import Assessment, EvidenceLabel, MLLabel


# Pagsamahin ang model label at evidence verdict sa final assessment.
def decide(ml: MLLabel, evidence: EvidenceLabel) -> Assessment:
    if evidence is EvidenceLabel.INSUFFICIENT:
        # Kung kulang ang evidence, markahang unverified ang model estimate.
        if ml is MLLabel.RELIABLE:
            return Assessment.UNVERIFIED_RELIABLE
        return Assessment.UNVERIFIED_MISINFORMATION
    if ml is MLLabel.RELIABLE and evidence is EvidenceLabel.SUPPORTED:
        return Assessment.STRONG_SUPPORT
    if ml is MLLabel.MISINFORMATION and evidence is EvidenceLabel.CONTRADICTED:
        return Assessment.LIKELY_MISINFORMATION
    return Assessment.CONFLICTING
