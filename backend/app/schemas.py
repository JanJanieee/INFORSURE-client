from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class MLLabel(StrEnum):
    RELIABLE = "Reliable"
    MISINFORMATION = "Misinformation"


class EvidenceLabel(StrEnum):
    SUPPORTED = "Supported"
    CONTRADICTED = "Contradicted"
    INSUFFICIENT = "Insufficient Evidence"


class UserFeedback(StrEnum):
    AGREE = "Agree"
    DISAGREE = "Disagree"
    FLAG = "Flag"


class Scope(StrEnum):
    OUT_OF_SCOPE = "out_of_scope"
    NO_VERIFIABLE_CLAIM = "no_verifiable_health_claim"
    VERIFIED = "verified"


class Assessment(StrEnum):
    STRONG_SUPPORT = "Supported / strong agreement"
    LIKELY_MISINFORMATION = "Likely misinformation / strong agreement"
    CONFLICTING = "Conflicting assessment"
    # No usable evidence: the model estimate is still shown, clearly marked as not verified.
    UNVERIFIED_RELIABLE = "Not verified: model estimate is Reliable / use caution"
    UNVERIFIED_MISINFORMATION = "Not verified: model estimate is Misinformation / use caution"


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    # "image": the text was read from an image; the whole text is checked as one claim (docx 16.4 exception).
    source: Literal["text", "image"] = "text"


class EvidenceItem(BaseModel):
    evidence_id: int
    evidence_text: str
    source_name: str
    source_url: str
    publication_date: str | None = None
    similarity: float
    relation: str | None = None  # entailment / neutral / contradiction (claim vs this passage)
    relation_score: float | None = None


class AnalyzeResponse(BaseModel):
    scope: Scope
    message: str | None = None
    claim: str | None = None
    ml_label: MLLabel | None = None
    ml_confidence: float | None = None
    evidence_result: EvidenceLabel | None = None
    assessment: Assessment | None = None
    evidence: list[EvidenceItem] = []
    model_version: str | None = None
    truncated: bool = False  # image mode only: the text was cut to the claim length limit


class FeedbackRequest(BaseModel):
    claim_text: str = Field(min_length=1, max_length=5000)
    model_prediction: MLLabel
    model_confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_result: EvidenceLabel | None = None
    user_feedback: UserFeedback
    model_version: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    review_status: str


class OcrLine(BaseModel):
    text: str
    score: float


class OcrResponse(BaseModel):
    text: str
    lines: list[OcrLine]
    mean_score: float
    low_confidence: bool
    width: int
    height: int
    engine: str
