"""Mga hakbang mula scope checks hanggang evidence verification."""
from contextlib import closing

from .. import config, db
from ..schemas import EvidenceItem, EvidenceLabel, MLLabel
from . import evidence_index, lexicon, nli, verification
from .model_store import load_model


# I-check ang health terms gamit ang lexicon.
def is_health_related(text: str) -> bool:
    return lexicon.is_health_text(text)


# I-check kung may factual health assertion sa text.
def has_verifiable_claim(text: str) -> bool:
    return any(lexicon.is_claim_like(s) for s in lexicon.sentences(text))


def extract_claim(text: str) -> str:
    """Kunin ang unang checkable health sentence."""
    for sentence in lexicon.sentences(text):
        if lexicon.is_claim_like(sentence):
            return sentence
    return text.strip()


def whole_text_claim(text: str) -> tuple[str, bool]:
    """Gamitin ang buong image text; putulin kung lampas sa limit."""
    from .. import config

    claim = " ".join(text.split())
    limit = config.IMAGE_CLAIM_MAX_CHARS
    if len(claim) <= limit:
        return claim, False
    cut = claim[:limit]
    boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if boundary >= limit * 0.6:          # Unahin ang dulo ng sentence bilang putulan.
        return cut[: boundary + 1], True
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut), True


def classify(claim: str) -> tuple[MLLabel, float, str]:
    """Ibalik ang label, confidence at model version; hindi truth probability."""
    classifier = load_model()
    label, confidence = classifier.predict(claim)
    return MLLabel(label), confidence, classifier.version


def retrieve_evidence(claim: str) -> list[EvidenceItem]:
    """Hanapin ang relevant passages mula sa Validated evidence lang."""
    db.init_db()
    with closing(db.connect()) as conn:
        return evidence_index.search(conn, claim)


def verify(claim: str, evidence: list[EvidenceItem]) -> tuple[EvidenceLabel, list[EvidenceItem]]:
    """I-score ang passages gamit ang NLI, saka buuin ang evidence verdict."""
    if not evidence:
        return EvidenceLabel.INSUFFICIENT, []
    probs = nli.predict([e.evidence_text for e in evidence], [claim] * len(evidence))
    annotated = []
    for item, p in zip(evidence, probs):
        best = int(p.argmax())
        annotated.append(item.model_copy(update={"relation": nli.ORDER[best], "relation_score": float(p[best])}))
    return verification.aggregate(probs, config.NLI_MIN_CONFIDENCE), annotated
