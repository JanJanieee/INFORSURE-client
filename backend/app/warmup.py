"""I-load ang models sa startup at i-report kung ready o may error."""
import logging
import threading
import time

from . import config

log = logging.getLogger("uvicorn.error")

_ready = threading.Event()
_state: dict = {"warming": False, "error": None, "seconds": None}


# I-load ang embeddings, OCR, NLI at selected classifier.
def _load_all() -> None:
    from . import ocr
    from .pipeline import embeddings, nli
    from .pipeline.model_store import ModelNotAvailable, load_model

    embeddings.embed(["warm up"])
    try:
        ocr.get_engine()  # Puwedeng tumuloy ang text flow kahit unavailable ang OCR.
    except ocr.OcrUnavailable as exc:
        _state["error"] = str(exc)
    nli.predict(["warm up passage"], ["warm up claim"])
    try:
        load_model()
    except ModelNotAvailable as exc:  # Ibalik sa /analyze ang dahilan kung unavailable ang classifier.
        _state["error"] = str(exc)


def start() -> threading.Thread | None:
    """Simulan ang background warmup kung naka-enable."""
    _ready.clear()
    _state.update(warming=False, error=None, seconds=None)
    if not config.WARMUP:
        _ready.set()
        return None
    _state["warming"] = True

    # I-load ang models at itala ang oras o error.
    def run() -> None:
        began = time.time()
        try:
            _load_all()
            log.info("InforSure models ready in %.0f s", time.time() - began)
        except Exception as exc:  # noqa: BLE001  Panatilihin ang server; puwedeng mag-load sa first use.
            _state["error"] = f"{type(exc).__name__}: {exc}"
            log.exception("InforSure warm-up failed")
        finally:
            _state["seconds"] = round(time.time() - began, 1)
            _state["warming"] = False
            _ready.set()

    thread = threading.Thread(target=run, name="infosure-warmup", daemon=True)
    thread.start()
    return thread


# Ibalik ang ready/warming status, error at loading time.
def status() -> dict:
    return {"ready": _ready.is_set(), "warming": _state["warming"], "error": _state["error"], "seconds": _state["seconds"]}


# Hintayin ang warmup hanggang sa time limit.
def wait_until_ready(timeout: float | None = None) -> bool:
    return _ready.wait(config.WARMUP_WAIT_SECONDS if timeout is None else timeout)
