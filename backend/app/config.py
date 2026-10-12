import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = Path(os.environ.get("INFOSURE_DB", ROOT / "data" / "infosure.db"))
MODELS_DIR = Path(os.environ.get("INFOSURE_MODELS_DIR", ROOT / "models"))
INDEX_DIR = Path(os.environ.get("INFOSURE_INDEX_DIR", ROOT / "data" / "index"))
# Word lists for the scope check: health terms, question starts, opinion starts (one sheet each; edit the workbook).
LEXICON_PATH = Path(os.environ.get("INFOSURE_LEXICON", ROOT / "data" / "lexicon" / "lexicon.xlsx"))

EMBEDDING_MODEL = os.environ.get(
    "INFOSURE_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
RETRIEVAL_TOP_K = int(os.environ.get("INFOSURE_TOP_K", "3"))
# Placeholder: cosine similarity below this means "no relevant evidence" (-> Insufficient Evidence).
# Tune on validated claim/evidence pairs (HealthVer) before trusting it.
SIMILARITY_MIN = float(os.environ.get("INFOSURE_SIMILARITY_MIN", "0.40"))

# Load the models at server start (about a minute) instead of on the first request. 0 = off (tests).
WARMUP = os.environ.get("INFOSURE_WARMUP", "1") != "0"
# How long /analyze waits for the warm-up to finish before it tries to load the models itself.
WARMUP_WAIT_SECONDS = float(os.environ.get("INFOSURE_WARMUP_WAIT", "180"))

# OCR (text inside images). All local; images are never stored or sent anywhere.
OCR_ENGINE = os.environ.get("INFOSURE_OCR_ENGINE", "rapidocr")
OCR_MAX_BYTES = int(os.environ.get("INFOSURE_OCR_MAX_BYTES", str(5 * 1024 * 1024)))
# Average line confidence below this (or a very short text) shows a "may be misread" warning.
OCR_LOW_CONFIDENCE = float(os.environ.get("INFOSURE_OCR_LOW_CONFIDENCE", "0.75"))
# Image mode treats the whole text of the image as one claim, up to this many characters.
IMAGE_CLAIM_MAX_CHARS = int(os.environ.get("INFOSURE_IMAGE_CLAIM_MAX_CHARS", "800"))

# Multilingual NLI cross-encoder used for evidence verification (MIT license per its model card).
NLI_MODEL = os.environ.get("INFOSURE_NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
# Placeholder: a passage must entail/contradict the claim with at least this probability to count.
# Tune on HealthVer dev with `py -m training.eval_verifier` before trusting it.
NLI_MIN_CONFIDENCE = float(os.environ.get("INFOSURE_NLI_MIN_CONFIDENCE", "0.70"))
