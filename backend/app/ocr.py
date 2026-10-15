"""Basahin ang image text locally; walang image file na sine-save."""
import io
import re
import statistics
import threading
from dataclasses import dataclass
from typing import Protocol

from PIL import Image, ImageOps, UnidentifiedImageError

from . import config

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
MAX_PIXELS = 40_000_000  # Limitahan ang pixels bago i-decode.
MAX_SIDE = 2000          # Paliitin ang sobrang laking image.
MIN_LONG_SIDE = 900      # Palakihin ang maliit na image para mas mabasa.
MAX_UPSCALE = 3.0
MAX_TEXT_CHARS = 5000    # Pareho ng text limit sa /analyze.


class ImageError(ValueError):
    """Image error na may kasamang HTTP status."""

    # Itala ang image error kasama ang HTTP status.
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


class OcrUnavailable(RuntimeError):
    pass


@dataclass
class Line:
    text: str
    score: float
    top: float
    left: float
    height: float


@dataclass
class OcrResult:
    text: str
    lines: list[Line]
    mean_score: float
    width: int
    height: int
    engine: str
    dropped: int


class OcrEngine(Protocol):
    name: str

    def read(self, image: Image.Image) -> list[Line]:
        """Ibalik ang text lines na nakita sa image."""


# Ihanda ang image.

# I-validate at ihanda ang image para sa OCR.
def load_image(data: bytes, max_bytes: int | None = None) -> Image.Image:
    limit = config.OCR_MAX_BYTES if max_bytes is None else max_bytes
    if not data:
        raise ImageError("The file is empty.")
    if len(data) > limit:
        raise ImageError(f"The image is larger than {limit // (1024 * 1024)} MB.", status=413)
    try:
        image = Image.open(io.BytesIO(data))
        fmt = image.format
        width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageError("This file is not an image the server can read.", status=415) from exc
    if fmt not in ALLOWED_FORMATS:
        raise ImageError("Use a PNG, JPG, or WebP image.", status=415)
    if width * height > MAX_PIXELS:
        raise ImageError("The image has too many pixels.", status=422)
    try:
        image = ImageOps.exif_transpose(image)  # Sundin ang photo rotation sa metadata.
        if image.mode in ("RGBA", "LA", "P"):
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            background.alpha_composite(rgba)  # White background para hindi matakpan ang dark text.
            image = background
        image = image.convert("RGB")
    except (OSError, ValueError) as exc:
        raise ImageError("The image could not be decoded.", status=422) from exc

    long_side = max(image.size)
    if long_side > MAX_SIDE:
        scale = MAX_SIDE / long_side
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    elif long_side < MIN_LONG_SIDE:
        scale = min(MAX_UPSCALE, MIN_LONG_SIDE / long_side)
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    return image


# Linisin ang nabasang text.

# Alisin ang buong UI line, hindi ang kaparehong salita sa claim.
_CHROME = [
    r"like|comment|share|reply|follow|send|save|more|see more|see less|see translation|view more comments?|"
    r"write a comment\.*|most relevant|all comments|sponsored|suggested for you|like page|learn more|shop now|"
    r"gusto ko|magkomento|i-?share|tumugon|sundan|tingnan ang iba pa|tingnan ang salin",
    r"\d+([.,]\d+)?\s?[kKmM]?",                                      # Bilang ng reactions.
    r"\d+([.,]\d+)?\s?[kKmM]?\s+(comments?|shares?|likes?|views?|reactions?|komento|pagbabahagi)",
    r"(just now|yesterday|today|\d+\s?(s|m|min|mins|h|hr|hrs|d|w|y)|\d+\s+(seconds?|minutes?|hours?|days?|weeks?) ago)",
    r"(yesterday|today|(january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2})"
    r"( at \d{1,2}:\d{2}\s?(am|pm)?)?",
]
_CHROME_RE = re.compile(r"^(?:%s)$" % "|".join(f"(?:{p})" for p in _CHROME), re.IGNORECASE)
MIN_LINE_SCORE = 0.5


# I-check kung UI text lang ang buong line.
def _is_chrome(text: str) -> bool:
    return bool(_CHROME_RE.match(text.strip(" .·•-|")))


def _reading_order(lines: list[Line]) -> list[Line]:
    """Ayusin ang single-column lines mula taas, saka kaliwa."""
    if not lines:
        return []
    typical = statistics.median(max(l.height, 1.0) for l in lines)
    ordered = sorted(lines, key=lambda l: l.top)
    rows: list[list[Line]] = []
    for line in ordered:
        if rows and abs(line.top - rows[-1][0].top) < 0.5 * typical:
            rows[-1].append(line)
        else:
            rows.append([line])
    return [l for row in rows for l in sorted(row, key=lambda l: l.left)]


# Pagdugtungin ang lines; ayusin ang naputol na salita.
def _join(texts: list[str]) -> str:
    out = ""
    for text in texts:
        text = " ".join(text.split())
        if not text:
            continue
        if out.endswith("-") and text[:1].islower():
            out = out[:-1] + text          # Halimbawa: treat- + ment -> treatment.
        else:
            out = f"{out} {text}".strip()
    return out


def clean(lines: list[Line]) -> tuple[str, list[Line], int]:
    """Alisin ang mahinang/UI lines; ibalik ang text at counts."""
    kept = [l for l in lines if l.text.strip() and l.score >= MIN_LINE_SCORE and not _is_chrome(l.text)]
    dropped = len(lines) - len(kept)
    kept = _reading_order(kept)
    text = _join([l.text for l in kept])
    return text[:MAX_TEXT_CHARS].strip(), kept, dropped


# Ihanda ang OCR engine.

class RapidOcrEngine:
    """RapidOCR reader na gumagamit ng ONNX Runtime sa CPU."""

    name = "rapidocr"

    # Ihanda ang RapidOCR at lock para sa sabay na requests.
    def __init__(self) -> None:
        from rapidocr import RapidOCR

        self._engine = RapidOCR()
        self._lock = threading.Lock()

    # Basahin ang image bilang text, scores at line positions.
    def read(self, image: Image.Image) -> list[Line]:
        import numpy as np

        with self._lock:
            out = self._engine(np.array(image))
        if out is None or out.txts is None or len(out.txts) == 0:
            return []
        lines = []
        for text, score, box in zip(out.txts, out.scores, out.boxes):
            ys = [float(p[1]) for p in box]
            xs = [float(p[0]) for p in box]
            lines.append(Line(str(text), float(score), min(ys), min(xs), max(ys) - min(ys)))
        return lines


ENGINES = {"rapidocr": RapidOcrEngine}
_engine: OcrEngine | None = None
_engine_lock = threading.Lock()


# Gamitin ulit ang OCR engine; gumawa kung wala pa.
def get_engine() -> OcrEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            try:
                factory = ENGINES[config.OCR_ENGINE]
            except KeyError as exc:
                raise OcrUnavailable(f"Unknown OCR engine '{config.OCR_ENGINE}' (known: {', '.join(ENGINES)}).") from exc
            try:
                _engine = factory()
            except Exception as exc:  # noqa: BLE001  Kulang ang package o model files.
                raise OcrUnavailable(f"The OCR engine could not start: {exc}") from exc
        return _engine


# I-run ang image validation, OCR at text cleanup.
def read_image(data: bytes) -> OcrResult:
    image = load_image(data)
    engine = get_engine()
    lines = engine.read(image)
    text, kept, dropped = clean(lines)
    mean = sum(l.score for l in kept) / len(kept) if kept else 0.0
    return OcrResult(text=text, lines=kept, mean_score=round(mean, 3), width=image.width, height=image.height,
                     engine=engine.name, dropped=dropped)


def is_low_confidence(result: OcrResult) -> bool:
    """I-check kung kailangang i-review ang OCR text."""
    return bool(result.text) and (result.mean_score < config.OCR_LOW_CONFIDENCE or len(result.text) < 15)
