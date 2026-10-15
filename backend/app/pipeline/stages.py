"""Pipeline stages (thesis section 3).

Implemented: health-domain check, verifiable-claim check, claim extraction, ML classification, retrieval, verification.
Retrieval returns [] when no validated passage is similar enough, and the result is then
`Insufficient Evidence`. Verification scores claim vs passage with a multilingual NLI model.

Keep the signatures stable: the Phase 2 automatic mode reuses the same stages per claim.
"""
from contextlib import closing

from .. import config, db
from ..schemas import EvidenceItem, EvidenceLabel, MLLabel
from . import evidence_index, lexicon, nli, verification
from .model_store import load_model


def is_health_related(text: str) -> bool:
    return lexicon.is_health_text(text)


def has_verifiable_claim(text: str) -> bool:
    return any(lexicon.is_claim_like(s) for s in lexicon.sentences(text))


def extract_claim(text: str) -> str:
    """Isolate the first checkable health assertion. Phase 1 verifies one claim per selection."""
    for sentence in lexicon.sentences(text):
        if lexicon.is_claim_like(sentence):
            return sentence
    return text.strip()


def whole_text_claim(text: str) -> tuple[str, bool]:
    """Image mode: the whole text of the image is one claim. Returns (claim, truncated)."""
    from .. import config

    claim = " ".join(text.split())
    limit = config.IMAGE_CLAIM_MAX_CHARS
    if len(claim) <= limit:
        return claim, False
    cut = claim[:limit]
    boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if boundary >= limit * 0.6:          # prefer to stop at the end of a sentence
        return cut[: boundary + 1], True
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut), True


def classify(claim: str) -> tuple[MLLabel, float, str]:
    """Return (label, confidence, model_version) from whichever model is loaded (see model_store).

    SVM uses an uncalibrated margin score; the transformer uses validation-temperature
    softmax. Neither score is a probability that the claim is factually true.
    """
    classifier = load_model()
    label, confidence = classifier.predict(claim)
    return MLLabel(label), confidence, classifier.version


def retrieve_evidence(claim: str) -> list[EvidenceItem]:
    """Search validated evidence only (view `validated_evidence`) through the vector index."""
    db.init_db()
    with closing(db.connect()) as conn:
        return evidence_index.search(conn, claim)


def verify(claim: str, evidence: list[EvidenceItem]) -> tuple[EvidenceLabel, list[EvidenceItem]]:
    """Compare the claim with each retrieved passage (NLI) and aggregate.

    Returns the verdict and the passages annotated with their relation to the claim. No evidence, or only
    weak/neutral/conflicting evidence, gives INSUFFICIENT, never a fake verdict.
    """
    if not evidence:
        return EvidenceLabel.INSUFFICIENT, []
    probs = nli.predict([e.evidence_text for e in evidence], [claim] * len(evidence))
    annotated = []
    for item, p in zip(evidence, probs):
        best = int(p.argmax())
        annotated.append(item.model_copy(update={"relation": nli.ORDER[best], "relation_score": float(p[best])}))
    return verification.aggregate(probs, config.NLI_MIN_CONFIDENCE), annotated
