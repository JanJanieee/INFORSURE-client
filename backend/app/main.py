# API routes para sa claim analysis, OCR, status at feedback.
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from . import config, db, ocr, warmup
from .pipeline.evidence_index import EvidenceIndexStale
from .pipeline.model_store import ModelNotAvailable
from .pipeline.run import analyze
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FeedbackRequest,
    FeedbackResponse,
    OcrLine,
    OcrResponse,
)


# Ihanda ang DB at simulan ang model warmup.
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    warmup.start()
    yield


app = FastAPI(title="InforSure API", version="0.1.0", lifespan=lifespan)


# Ibalik kung buhay ang API server.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def model_status() -> dict:
    """Ibalik ang model readiness, loading time at anumang error."""
    return warmup.status()


# Hintayin ang models, saka i-analyze ang claim.
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_text(req: AnalyzeRequest) -> AnalyzeResponse:
    warmup.wait_until_ready()  # Hintayin ang startup loading bago mag-analyze.
    try:
        return analyze(req.text, req.source)
    except (ModelNotAvailable, EvidenceIndexStale) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=f"Not implemented: {exc}")


@app.post("/ocr", response_model=OcrResponse)
def read_text_from_image(file: UploadFile = File(...)) -> OcrResponse:
    """Basahin ang image text sa memory; walang image file na sine-save."""
    warmup.wait_until_ready()
    data = file.file.read(config.OCR_MAX_BYTES + 1)
    try:
        result = ocr.read_image(data)
    except ocr.ImageError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
    except ocr.OcrUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return OcrResponse(
        text=result.text,
        lines=[OcrLine(text=l.text, score=round(l.score, 3)) for l in result.lines],
        mean_score=result.mean_score,
        low_confidence=ocr.is_low_confidence(result),
        width=result.width,
        height=result.height,
        engine=result.engine,
    )


@app.post("/feedback", response_model=FeedbackResponse, status_code=201)
def submit_feedback(
    req: FeedbackRequest, conn: sqlite3.Connection = Depends(db.get_conn)
) -> FeedbackResponse:
    """I-save bilang Pending; kailangan ng review bago training."""
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO feedback (claim_text, model_prediction, model_confidence, "
                "evidence_result, user_feedback, model_version) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    req.claim_text,
                    req.model_prediction.value,
                    req.model_confidence,
                    req.evidence_result.value if req.evidence_result else None,
                    req.user_feedback.value,
                    req.model_version,
                ),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=422, detail="Unknown model_version")
    return FeedbackResponse(feedback_id=cur.lastrowid, review_status="Pending")
