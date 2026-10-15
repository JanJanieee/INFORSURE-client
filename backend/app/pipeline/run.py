# Dito nakaayos ang buong claim-analysis flow.
from ..schemas import AnalyzeResponse, Scope
from . import stages
from .decision import decide


# I-run ang claim checks, classification, retrieval at final assessment.
def analyze(text: str, source: str = "text") -> AnalyzeResponse:
    if not stages.is_health_related(text):
        return AnalyzeResponse(
            scope=Scope.OUT_OF_SCOPE,
            message="The selected text is outside the health domain.",
        )
    if not stages.has_verifiable_claim(text):
        return AnalyzeResponse(
            scope=Scope.NO_VERIFIABLE_CLAIM,
            message="No Verifiable Health Claim Detected",
        )

    if source == "image":
        claim, truncated = stages.whole_text_claim(text)
    else:
        claim, truncated = stages.extract_claim(text), False
    ml_label, ml_confidence, model_version = stages.classify(claim)
    evidence = stages.retrieve_evidence(claim)
    evidence_result, evidence = stages.verify(claim, evidence)

    return AnalyzeResponse(
        scope=Scope.VERIFIED,
        claim=claim,
        ml_label=ml_label,
        ml_confidence=ml_confidence,
        evidence_result=evidence_result,
        assessment=decide(ml_label, evidence_result),
        evidence=evidence,
        model_version=model_version,
        truncated=truncated,
    )
