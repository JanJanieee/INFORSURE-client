"""Load the models when the server starts, not on the first request.

Loading the embedding and NLI models takes about a minute on this machine (GPU start-up included). Done lazily, the
first check after every server start looked frozen. Here it runs in a background thread at start-up: the server
answers /health and /status at once, `/status` says whether the models are ready, and `/analyze` waits for them.

Set INFOSURE_WARMUP=0 to skip (tests do this). A failed warm-up is not fatal: the models then load on first use
as before, and the error is shown by `/status`.
"""
import logging
import threading
import time

from . import config

log = logging.getLogger("uvicorn.error")

_ready = threading.Event()
_state: dict = {"warming": False, "error": None, "seconds": None}


def _load_all() -> None:
    from . import ocr
    from .pipeline import embeddings, nli
    from .pipeline.model_store import ModelNotAvailable, load_model

    embeddings.embed(["warm up"])
    try:
        ocr.get_engine()  # the text-in-image reader; optional, so a failure here is not fatal
    except ocr.OcrUnavailable as exc:
        _state["error"] = str(exc)
    nli.predict(["warm up passage"], ["warm up claim"])
    try:
        load_model()
    except ModelNotAvailable as exc:  # no deployed model yet: /analyze answers 503 with the reason
        _state["error"] = str(exc)


def start() -> threading.Thread | None:
    """Begin loading in the background. Returns the thread, or None when warm-up is switched off."""
    _ready.clear()
    _state.update(warming=False, error=None, seconds=None)
    if not config.WARMUP:
        _ready.set()
        return None
    _state["warming"] = True

    def run() -> None:
        began = time.time()
        try:
            _load_all()
            log.info("InforSure models ready in %.0f s", time.time() - began)
        except Exception as exc:  # noqa: BLE001  keep the server up; models load on first use instead
            _state["error"] = f"{type(exc).__name__}: {exc}"
            log.exception("InforSure warm-up failed")
        finally:
            _state["seconds"] = round(time.time() - began, 1)
            _state["warming"] = False
            _ready.set()

    thread = threading.Thread(target=run, name="infosure-warmup", daemon=True)
    thread.start()
    return thread


def status() -> dict:
    return {"ready": _ready.is_set(), "warming": _state["warming"], "error": _state["error"], "seconds": _state["seconds"]}


def wait_until_ready(timeout: float | None = None) -> bool:
    return _ready.wait(config.WARMUP_WAIT_SECONDS if timeout is None else timeout)
