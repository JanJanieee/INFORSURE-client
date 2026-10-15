# Dito ang shared paths, model settings at limits.
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = Path(os.environ.get("INFOSURE_DB", ROOT / "data" / "infosure.db"))
MODELS_DIR = Path(os.environ.get("INFOSURE_MODELS_DIR", ROOT / "models"))
INDEX_DIR = Path(os.environ.get("INFOSURE_INDEX_DIR", ROOT / "data" / "index"))
# Excel lists para sa health, question at opinion checks.
LEXICON_PATH = Path(os.environ.get("INFOSURE_LEXICON", ROOT / "data" / "lexicon" / "lexicon.xlsx"))

EMBEDDING_MODEL = os.environ.get(
    "INFOSURE_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
RETRIEVAL_TOP_K = int(os.environ.get("INFOSURE_TOP_K", "3"))
# Provisional: below nito, walang relevant evidence.
# I-tune gamit ang labeled claim-evidence pairs.
SIMILARITY_MIN = float(os.environ.get("INFOSURE_SIMILARITY_MIN", "0.40"))

# I-load sa startup; 0 para i-skip ang warmup.
WARMUP = os.environ.get("INFOSURE_WARMUP", "1") != "0"
# Tagal ng paghihintay bago subukang mag-load sa request.
WARMUP_WAIT_SECONDS = float(os.environ.get("INFOSURE_WARMUP_WAIT", "180"))

# Local OCR lang; walang image file na sine-save.
OCR_ENGINE = os.environ.get("INFOSURE_OCR_ENGINE", "rapidocr")
OCR_MAX_BYTES = int(os.environ.get("INFOSURE_OCR_MAX_BYTES", str(5 * 1024 * 1024)))
# Ipa-review ang maikli o mababang-confidence na OCR text.
OCR_LOW_CONFIDENCE = float(os.environ.get("INFOSURE_OCR_LOW_CONFIDENCE", "0.75"))
# Buong image text ang claim, hanggang sa character limit.
IMAGE_CLAIM_MAX_CHARS = int(os.environ.get("INFOSURE_IMAGE_CLAIM_MAX_CHARS", "800"))

# Separate NLI model para sa evidence verification; MIT license.
NLI_MODEL = os.environ.get("INFOSURE_NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
# Provisional: minimum NLI score para sa support o contradiction.
# I-tune gamit ang hiwalay na labeled claim-evidence pairs.
NLI_MIN_CONFIDENCE = float(os.environ.get("INFOSURE_NLI_MIN_CONFIDENCE", "0.70"))
