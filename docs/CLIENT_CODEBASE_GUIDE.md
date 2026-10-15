# INFORSURE-client: Folder, File and Continuation Guide

Client technical handover | Version 1.2 | Updated 15 October 2026

Codebase reference: client commit `9104f74` and the supplied `v0.2-xlmr-pubhealth-en-exp` model package.

## 1. Purpose and scope

This guide explains how the client repository is organized, why each folder exists, and what every supplied file does. It is intended for the client and developers who will maintain the system or continue English model training. Installation commands and operating instructions remain in the root README; this guide explains the files those instructions use.

The guide covers all 64 files in the delivered source commit, the documentation and empty collection template added with this guide, and the important files created or downloaded later. Sections 11-21 provide the client continuation workflow, from English data collection and Excel formatting through cleaning, training, model selection, feedback and evidence maintenance. Entries explicitly identify supporting code that is available but is not the active classifier path.

Paths are relative to the project root. For example, backend/app/main.py means the main.py file inside app, inside backend. A package is a folder that Python can import. A module is usually one .py file. An artifact is a saved data/model file used by code.

## 2. How the system fits together

The Chrome extension captures a selected claim or image input. The local backend checks the text, runs the trained classifier, finds relevant reviewed evidence, compares that evidence with the claim, and returns a result with references. SQLite stores evidence and feedback; the training pipeline is used separately when a developer deliberately trains another version.

```text
Chrome extension
  -> optional image-to-text OCR
  -> health and question/opinion checks
  -> claim extraction
  -> English-trained XLM-RoBERTa label and confidence
  -> semantic retrieval from Validated SQLite evidence
  -> NLI comparison of claim and retrieved passages
  -> evidence verdict and final assessment
  -> result displayed in the extension
  -> optional user feedback saved as Pending
```

Three model roles appear in this flow:


| Component | Purpose | Stored or obtained from |
| --- | --- | --- |
| XLM-RoBERTa classifier | Estimates Reliable or Misinformation from the claim text. | Versioned files under models/v0.2-xlmr-pubhealth-en-exp/. Learned weights arrive in the release ZIP. |
| MiniLM embedding model | Represents claims/passages as vectors so retrieval can find related evidence. | Downloaded to the model cache; data/index/ holds the resulting evidence vectors. |
| mDeBERTa NLI model | Estimates whether a retrieved passage entails, contradicts or is neutral toward the claim. | Downloaded to the model cache; configured in backend/app/config.py. |


These roles are separate. The evidence index, SQLite database, CSV and architecture JSON are not alternative copies of the classifier. The supplied trained classifier uses model.safetensors; a .pkl file is not required for this package. RapidOCR is an additional image-reading component.

## 3. Source folder structure

The following tree shows repository files, including this guide. Downloaded/generated files are described separately in Section 5 so a fresh clone is easy to compare against this map.

```text
INFORSURE-client/
├── .gitattributes
├── .gitignore
├── README.md
├── THIRD_PARTY_NOTICES.md
├── backend/
│   ├── __init__.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dataset_version.py
│   │   ├── db.py
│   │   ├── deploy.py
│   │   ├── handoff.py
│   │   ├── ingest.py
│   │   ├── main.py
│   │   ├── model_download.py
│   │   ├── ocr.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── decision.py
│   │   │   ├── embeddings.py
│   │   │   ├── evidence_index.py
│   │   │   ├── lexicon.py
│   │   │   ├── model_store.py
│   │   │   ├── nli.py
│   │   │   ├── prediction.py
│   │   │   ├── run.py
│   │   │   ├── stages.py
│   │   │   ├── transformer_classifier.py
│   │   │   └── verification.py
│   │   ├── review.py
│   │   ├── schema.sql
│   │   ├── schemas.py
│   │   └── warmup.py
│   └── requirements.txt
├── data/
│   ├── index/
│   │   ├── index.json
│   │   └── vectors.npy
│   ├── infosure.db
│   ├── lexicon/
│   │   └── lexicon.xlsx
│   └── training/
│       └── pubhealth_v1.csv
├── docs/
│   ├── CLIENT_CODEBASE_GUIDE.md
│   ├── INFORSURE_Client_Guide.docx
│   └── templates/
│       └── english_claims_template.xlsx
├── extension/
│   ├── background.js
│   ├── content.js
│   ├── manifest.json
│   ├── sidepanel.css
│   ├── sidepanel.html
│   └── sidepanel.js
├── models/
│   ├── active.json
│   ├── download.json
│   └── v0.2-xlmr-pubhealth-en-exp/
│       ├── config.json
│       ├── metadata.json
│       ├── temperature.txt
│       ├── tokenizer.json
│       └── tokenizer_config.json
├── setup-demo.ps1
├── start-demo.ps1
└── training/
    ├── __init__.py
    ├── classical.py
    ├── configs/
    │   ├── default.json
    │   └── english_xlmr.json
    ├── evaluate.py
    ├── package.py
    ├── prepare/
    │   ├── __init__.py
    │   └── clean.py
    ├── requirements.txt
    ├── run.py
    ├── split.py
    └── transformer.py
```

## 4. Folder-by-folder and file-by-file reference


### 4.1. Project root: ./

The root is the starting point for installation, running the backend, and finding project guidance. Its scripts coordinate files in the other folders.


| File | What it does | When it is used |
| --- | --- | --- |
| [.gitattributes](../.gitattributes) | Tells Git how to store selected files. Database, NumPy, Excel, the supplied CSV and tokenizer artifacts are treated as binary so their bytes stay consistent across Windows and other systems. | Repository maintenance; helps preserve checksums. |
| [.gitignore](../.gitignore) | Lists local files and generated outputs Git should normally leave untracked, including the virtual environment, caches, runtime DB, downloaded weights and new training outputs. It contains an exception for the supplied evidence snapshot and English dataset. | Repository maintenance. Ignore rules do not remove files already committed or erase history. |
| [README.md](../README.md) | Provides the working setup and usage instructions: Python requirements, private model download, starting the backend, loading the extension, English training and evidence maintenance. | Read first when installing or operating the system. |
| [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) | Records attribution and license notices for PUBHEALTH and the XLM-RoBERTa base model, plus references for other downloaded components. | Reference when distributing or maintaining the project. |
| [setup-demo.ps1](../setup-demo.ps1) | Creates .venv, installs CPU-compatible runtime dependencies, installs and verifies the supplied classifier ZIP, prepares the runtime DB, and loads/downloads supporting models. -IncludeTraining installs additional training dependencies; -ModelArchive accepts a saved model ZIP. | One-time setup, or repair of an existing setup. It does not train a classifier. |
| [start-demo.ps1](../start-demo.ps1) | Selects the model from models/active.json, or from -ModelVersion; sets the runtime DB and cache paths; checks the assets; then launches Uvicorn on 127.0.0.1:8000. -Offline requests cached supporting models. | Each backend session. Keep its terminal open; Ctrl+C stops the server. |

### 4.2. Backend package: backend/

Contains the Python server and its dependency list. The extension sends requests here; the backend performs OCR, classification, retrieval, evidence verification and feedback storage.


| File | What it does | When it is used |
| --- | --- | --- |
| [__init__.py](../backend/__init__.py) | Marks backend as a Python package so modules can be imported and launched with commands such as python -m backend.app.handoff. | Python package structure; no business logic. |
| [requirements.txt](../backend/requirements.txt) | Pins the Python libraries used by the runtime, including FastAPI, Uvicorn, PyTorch, Transformers, sentence-transformers, RapidOCR, SQLite-related application support and Excel-reading support. SQLite itself comes with Python. | Installed by setup-demo.ps1. Training requirements reuse this list. |

### 4.3. Backend application: backend/app/

Contains API routes, shared settings, database access, OCR, startup preparation, and command-line maintenance tools. Most files here coordinate the detailed processing in pipeline/.


| File | What it does | When it is used |
| --- | --- | --- |
| [__init__.py](../backend/app/__init__.py) | Marks backend.app as a package. It allows imports between application modules and module-based command execution. | Python package structure; no processing stages. |
| [main.py](../backend/app/main.py) | Creates the FastAPI application. Defines GET /health and /status, POST /analyze, /ocr and /feedback, starts model warmup, and translates missing-model or stale-index failures into API errors. | API entry point used by Uvicorn and the extension. |
| [config.py](../backend/app/config.py) | Defines project paths, model identifiers and limits. Reads INFOSURE_* environment overrides for the DB, model/index directories, retrieval settings, OCR limits and warmup. The start script selects data/runtime/infosure.db. | Shared by runtime and maintenance modules. Changing a Python setting requires a backend restart. |
| [db.py](../backend/app/db.py) | Opens SQLite connections with foreign-key enforcement, creates tables from schema.sql, adds supported columns to older databases, and provides a per-request connection dependency. | Startup, API feedback storage, retrieval and maintenance tools. |
| [schema.sql](../backend/app/schema.sql) | Defines the database tables, constraints, indexes and validated_evidence view. Includes evidence, feedback and review records, dataset/model registrations, and links from dataset versions to reviewed feedback. | Executed by db.init_db(). Describes database structure, not its stored evidence content. |
| [schemas.py](../backend/app/schemas.py) | Defines Pydantic request/response structures and allowed labels. It validates text length and source mode and specifies prediction, evidence, assessment, OCR and feedback fields sent between server and extension. | API input validation and structured responses. |
| [warmup.py](../backend/app/warmup.py) | Loads embeddings, OCR, NLI and the classifier in a background thread when the server starts. Tracks ready/warming/error/seconds for /status and lets analysis wait for warmup. | Backend startup and readiness reporting. Check error as well as ready. |
| [handoff.py](../backend/app/handoff.py) | Checks that the classifier artifacts, lexicon, evidence snapshot and retrieval index are present and compatible. Creates the runtime DB if missing, preserves existing runtime feedback, and adds the selected model registration when upgrading. | Called by both PowerShell scripts. CLI commands: check, prepare, warmup. |
| [model_download.py](../backend/app/model_download.py) | Installs the trained classifier weights from the versioned release ZIP. Verifies archive/file sizes and SHA-256 checksums, validates archive entries, and installs the weights into the model folder. Supports --archive for a transferred ZIP and --verify for a local check. | Setup only; it does not download a new classifier for every claim. |
| [ocr.py](../backend/app/ocr.py) | Validates image input and uses RapidOCR with ONNX Runtime to read text. Organizes text lines, removes selected interface-like fragments, and reports recognition confidence and image dimensions. Images are processed in memory. | POST /ocr for image inputs; its extracted text later goes through /analyze. |
| [ingest.py](../backend/app/ingest.py) | Imports evidence from a CSV with source, url and text columns. Removes markup, splits articles into passages, preserves source/date/license information, skips duplicates and inserts new passages as Pending. | Manual evidence collection/import maintenance. New passages need human validation before retrieval. |
| [review.py](../backend/app/review.py) | Provides command-line tools to inspect and validate/reject evidence, review feedback with a human-approved label, and check/build the evidence index. Evidence status changes normally rebuild the index unless explicitly skipped. | Human review and evidence/index maintenance. It does not train automatically. |
| [dataset_version.py](../backend/app/dataset_version.py) | Creates a new training CSV from a base dataset plus reviewer-validated feedback. Uses the reviewer label, skips duplicates or label conflicts, records included feedback IDs, and preserves the base file. | Manual preparation for later training. Requires training dependencies and a language/provenance review. |
| [deploy.py](../backend/app/deploy.py) | Lists registered models and manages Candidate/Deployed/Retired states. Checks required artifacts and numerical acceptance criteria before deployment, and permits only one Deployed model at a time. | Model administration. Explicit selection by the client start script is separate from DB deployment status. |


The schema contains these application records:

| Table/view | Purpose |
| --- | --- |
| evidence | Evidence passages, source URLs, dates, review state, reviewer notes and embedding references. |
| validated_evidence (view) | Exposes only evidence records whose review_status is Validated. |
| feedback | Agree/Disagree/Flag events, the associated claim, model output/version and review state. |
| feedback_reviews | Human review decisions and the validated class label used for possible future training. |
| dataset_versions | Named dataset versions and their artifact references. |
| model_versions | Model registrations, dataset references, metrics and Candidate/Deployed/Retired status. |
| dataset_version_samples | Links a new dataset version to the specific reviewed feedback samples included in it. |

### 4.4. Processing pipeline: backend/app/pipeline/

Implements the ordered health-claim flow. The live path coordinates small modules rather than putting all behavior in an API route.


| File | What it does | When it is used |
| --- | --- | --- |
| [__init__.py](../backend/app/pipeline/__init__.py) | Marks the pipeline directory as a Python package so its stages and helper modules can be imported. | Python package structure. |
| [run.py](../backend/app/pipeline/run.py) | Coordinates analysis from beginning to end: scope checks, text/image claim selection, classification, evidence retrieval, NLI verification and the final decision. Builds the AnalyzeResponse including the model version. | Called by POST /analyze. This is the best starting file for reading the processing flow. |
| [stages.py](../backend/app/pipeline/stages.py) | Exposes the individual processing stages. Connects lexicon rules, model loading, retrieval and NLI; selects the first checkable sentence in text mode; caps image text at 800 characters by default; attaches evidence relation scores. | Called in order by pipeline/run.py. |
| [lexicon.py](../backend/app/pipeline/lexicon.py) | Reads the Excel workbook and builds matching rules for health terms, question phrases and opinion phrases. Splits sentences and checks whether a health assertion is claim-like. It uses rules and word lists, not the trained XLM classifier, for this initial filtering. | Scope checks and claim extraction. Unusual wording can be misjudged by these rules. |
| [model_store.py](../backend/app/pipeline/model_store.py) | Resolves the selected classifier version, reads its metadata, checks required artifacts and caches the loaded classifier. Chooses the transformer or supported scikit-learn loader from model_type. An explicit environment version takes priority over a DB Deployed record. | Classification/model loading. It does not silently select an arbitrary Candidate. |
| [transformer_classifier.py](../backend/app/pipeline/transformer_classifier.py) | Loads the packaged XLM-RoBERTa tokenizer and sequence-classification weights from local files. Tokenizes/truncates the claim, runs the model on an available CUDA device or CPU, applies temperature scaling and returns a label plus confidence. | Actual classifier inference for the supplied English model. |
| [prediction.py](../backend/app/pipeline/prediction.py) | Provides the shared prediction/confidence helper for supported scikit-learn pipelines: a probability for Naive Bayes or a margin-derived score for SVM. | Compatibility support for classical classifiers. The current XLM model uses transformer_classifier.py instead. |
| [embeddings.py](../backend/app/pipeline/embeddings.py) | Loads the sentence-transformer embedding model and turns texts into normalized numerical vectors. These vectors allow semantic similarity comparison between a claim and evidence passages. | Evidence index building and live retrieval. It does not assign Reliable/Misinformation labels. |
| [evidence_index.py](../backend/app/pipeline/evidence_index.py) | Builds and searches the vector index over Validated evidence only. Maps matching vector rows back to SQLite passages and sources; returns up to the configured top-k above the similarity threshold. Detects a missing or stale index. | Live evidence retrieval and manual index maintenance. |
| [nli.py](../backend/app/pipeline/nli.py) | Loads the separate mDeBERTa NLI model. Compares each evidence passage as the premise with the claim as the hypothesis, returning entailment, neutral and contradiction probabilities in a fixed order. | Evidence verification after retrieval; separate from the English claim classifier. |
| [verification.py](../backend/app/pipeline/verification.py) | Aggregates passage-level NLI probabilities into Supported, Contradicted or Insufficient Evidence. Strong support needs no strong contradiction, and vice versa. No evidence, weak relations or strong disagreement produce Insufficient Evidence. | Evidence verdict logic; no model loading or database writes. |
| [decision.py](../backend/app/pipeline/decision.py) | Combines the classifier label with the evidence verdict. Produces agreement, conflicting assessment, or an explicitly unverified model estimate when evidence is insufficient. | Final assessment logic; preserves the distinction between prediction and evidence. |

### 4.5. Stored application data: data/

Stores the supplied evidence snapshot, retrieval assets, editable rules and English training input. These serve different purposes and are not interchangeable.


| File | What it does | When it is used |
| --- | --- | --- |
| [infosure.db](../data/infosure.db) | SQLite source snapshot containing evidence and its source/review metadata, plus the supplied dataset/model registration. The handoff has 63 Validated retrievable passages and starts without the author's test feedback. Model weights are stored separately on disk. | Used to prepare the runtime DB. Normal operation through start-demo.ps1 uses a separate copy. |

### 4.6. Evidence retrieval index: data/index/

Stores the numerical search representation of the Validated evidence. Its metadata and vectors must match each other and the selected database evidence.


| File | What it does | When it is used |
| --- | --- | --- |
| [index.json](../data/index/index.json) | Records the embedding model ID, build time, ordered evidence IDs, content hash and vector dimension. The ID order connects each row in vectors.npy to its SQLite evidence record. | Index compatibility/staleness checks and evidence lookup. |
| [vectors.npy](../data/index/vectors.npy) | NumPy array containing the normalized evidence embeddings. The supplied index contains 63 vectors with 384 dimensions each. | Similarity search in evidence_index.py. This is an evidence search index, not classifier weights. |

### 4.7. Editable scope rules: data/lexicon/

Keeps the word and phrase lists used before classification in an Excel file that maintainers can inspect and update.


| File | What it does | When it is used |
| --- | --- | --- |
| [lexicon.xlsx](../data/lexicon/lexicon.xlsx) | Contains health_terms, questions and opinions sheets. Each sheet defines terms/phrases and matching behavior; supporting columns record language/category/notes. lexicon.py converts these entries to text-matching rules. | Health-domain and question/opinion filtering. Preserve sheet/column names and restart the backend after edits. |

### 4.8. English training input: data/training/

Contains the labeled corpus used for the supplied classifier. This data teaches classification patterns; it is not queried as the evidence repository during live checks.


| File | What it does | When it is used |
| --- | --- | --- |
| [pubhealth_v1.csv](../data/training/pubhealth_v1.csv) | Cleaned English PUBHEALTH input with 4,047 rows: 2,721 Reliable and 1,326 Misinformation. Columns include text, label, source, health_topic, unit, label_status, origin, group, fact_checker and language. It is preserved to match the model's recorded dataset checksum. | Offline training. Its old automatic language tags are imperfect; the supplied config declares English by PUBHEALTH origin. |

### 4.9. Chrome extension: extension/

Contains the browser interface and selection capture. Chrome loads this folder using Load unpacked. The Python backend runs separately on the same computer.


| File | What it does | When it is used |
| --- | --- | --- |
| [manifest.json](../extension/manifest.json) | Chrome Manifest V3 configuration. Declares the extension name/version, side panel, background service worker, page content script, permissions and allowed webpage hosts. | Chrome reads it when loading/reloading the extension. |
| [background.js](../extension/background.js) | Registers the behavior that opens the side panel when the extension toolbar icon is clicked. | Chrome background service worker. It does not perform classification. |
| [content.js](../extension/content.js) | Runs on supported webpages, watches selected text and forwards selection messages to the extension side panel. Answers selection/ping requests and guards against loading twice. | Browser-side text acquisition. Highlighting alone does not send text to the backend for analysis. |
| [sidepanel.html](../extension/sidepanel.html) | Defines the side-panel page structure, controls, text/image inputs, OCR review area and result containers. Loads the stylesheet and controller script. | Visible interface structure. |
| [sidepanel.css](../extension/sidepanel.css) | Defines visual presentation: layout, colors, spacing, light/dark themes, result cards, input states and responsive behavior. | Visible interface styling; no prediction logic. |
| [sidepanel.js](../extension/sidepanel.js) | Controls the interface, selection connection, image upload/paste/drop and OCR requests, analysis requests, loading/errors, result/evidence rendering, feedback, recent checks and display preferences. Calls the API at http://127.0.0.1:8000. | Main browser controller. EN/TL changes interface text, not the training dataset or input language. |

### 4.10. Model selection and distribution: models/

Stores the selected version, model-download manifest and versioned classifier package. Large trained weights are installed from a release asset rather than ordinary Git files.


| File | What it does | When it is used |
| --- | --- | --- |
| [active.json](../models/active.json) | Contains the default model_version read by the client setup/start scripts: v0.2-xlmr-pubhealth-en-exp. Changing the value selects another packaged version for the scripts. | Client model selection. model_store.py itself reads the environment or DB, not this file directly. |
| [download.json](../models/download.json) | Records the supplied model version, exact release ZIP URL, archive size/checksum and expected weight-file size/checksum. | Used by model_download.py to install and verify the supplied release package. |

### 4.11. Packaged English classifier: models/v0.2-xlmr-pubhealth-en-exp/

Contains files that belong together as one trained XLM-RoBERTa sequence classifier. The tokenizer prepares inputs, the architecture describes the network and the weights carry what it learned.


| File | What it does | When it is used |
| --- | --- | --- |
| [config.json](../models/v0.2-xlmr-pubhealth-en-exp/config.json) | Describes the XLM-RoBERTa architecture and label mapping. Identifies XLMRobertaForSequenceClassification and maps class 0 to Reliable and class 1 to Misinformation. | Read when constructing the classifier. It describes the model but does not contain its learned weights. |
| [metadata.json](../models/v0.2-xlmr-pubhealth-en-exp/metadata.json) | Records model/dataset versions, training time, English provenance, dataset checksum, configuration, evaluation metrics, acceptance gate, inference settings and library versions. | Model loading, maintenance, deployment checks and reproducibility reference. |
| [temperature.txt](../models/v0.2-xlmr-pubhealth-en-exp/temperature.txt) | Stores the validation-fitted confidence-calibration temperature, approximately 1.4 for this model. Inference divides logits by this value before applying softmax. | Used with the weights to calculate reported confidence. It is not a second classifier. |
| [tokenizer.json](../models/v0.2-xlmr-pubhealth-en-exp/tokenizer.json) | Stores the tokenizer vocabulary and text-to-token processing rules used to convert a claim into model inputs. | Loaded with the packaged classifier; must remain compatible with its weights. |
| [tokenizer_config.json](../models/v0.2-xlmr-pubhealth-en-exp/tokenizer_config.json) | Stores settings and special-token information needed when reconstructing the tokenizer through Transformers. | Read alongside tokenizer.json during local classifier loading. |


Additional required file after setup: model.safetensors contains the learned classifier weights (1,112,205,008 bytes, about 1.11 GB). It is installed here from the release asset and is intentionally absent from the ordinary source tree. Keep it with this folder's tokenizer, architecture, calibration and metadata files. Do not substitute an unrelated checkpoint with the same filename.


### 4.12. Offline training pipeline: training/

Provides the code needed to train and package a later model. These scripts run only when explicitly invoked; ordinary claim checks do not retrain the system.


| File | What it does | When it is used |
| --- | --- | --- |
| [__init__.py](../training/__init__.py) | Marks training as a package so its entry points and helpers can be imported or run with python -m. | Python package structure. |
| [requirements.txt](../training/requirements.txt) | Reuses backend/requirements.txt and adds pandas for CSV/dataframe processing. Setup installs it only when -IncludeTraining is requested, or it can be installed later. | Training and dataset-version preparation dependencies. |
| [run.py](../training/run.py) | Training entry point. Loads/validates labeled data and language provenance, creates splits, trains configured candidates, selects on validation results, evaluates on the held-out test split, applies the gate and packages the selected model. | Manual offline training. Writes run reports and refuses to overwrite an existing model directory. |
| [split.py](../training/split.py) | Creates reproducible train/validation/test sets by group and label. Uses the configured group column if present, otherwise normalized text, reducing exact duplicate overlap across splits. | Called before model training. It does not automatically identify all paraphrases or related sources. |
| [transformer.py](../training/transformer.py) | Fine-tunes XLM-RoBERTa using the training split with class-weighted loss, gradient accumulation and optional CUDA mixed precision. Retains the best validation epoch, fits a confidence temperature on validation, and saves weights/tokenizer/calibration. | Training-time implementation. Live inference uses backend/app/pipeline/transformer_classifier.py. |
| [evaluate.py](../training/evaluate.py) | Calculates accuracy, per-class precision/recall/F1, macro metrics, confusion matrix and example errors. Checks macro-F1 and class recall against the configured acceptance thresholds. | Training evaluation and deploy.py acceptance checks. These are necessary training functions, not the author's comparison scripts. |
| [package.py](../training/package.py) | Writes a new versioned model folder, saves the fitted transformer or supported classical artifact, records metadata/checksums and registers the model as Candidate in SQLite. | End of a training run. Does not automatically change the active model or deployment status. |
| [classical.py](../training/classical.py) | Contains reusable TF-IDF + Linear SVM and Naive Bayes candidate builders and exposes the shared prediction helper. The current English config selects transformer only. | Supporting training infrastructure. Enabling classical candidates requires suitable classical-model configuration; their old trained artifacts are not the current handoff model. |

### 4.13. Training configuration: training/configs/

Keeps training settings outside Python implementation code. Maintainers can create a new profile when changing approved English sources or training settings.


| File | What it does | When it is used |
| --- | --- | --- |
| [default.json](../training/configs/default.json) | Default profile used if training.run receives no --config. In this handoff it specifies the same English XLM-RoBERTa settings as english_xlmr.json, including seed, split ratios, origin declaration and acceptance gate. | Default offline training configuration. |
| [english_xlmr.json](../training/configs/english_xlmr.json) | Explicit English continuation profile: FacebookAI/xlm-roberta-base, English PUBHEALTH origin, 70/15/15 split, seed 42, 3 epochs, batch 4, accumulation 8, maximum length 128, macro-F1 >= 0.80 and each class recall >= 0.70. | Configuration named in the client README training command. New sources need explicit provenance/language review. |

### 4.14. Dataset preparation: training/prepare/

Provides cleaning utilities used before splitting/training and by the reviewed-feedback dataset builder.


| File | What it does | When it is used |
| --- | --- | --- |
| [__init__.py](../training/prepare/__init__.py) | Marks the preparation tools as a Python package for imports and module commands. | Python package structure. |
| [clean.py](../training/prepare/clean.py) | Normalizes whitespace/Unicode, removes short or invalid rows, drops duplicate and conflicting-label entries, and writes a new versioned CSV plus cleaning report. Preserves provenance columns and declares English for already checked English source data. | Manual data preparation and shared normalization helpers. It does not translate or automatically prove that input is English. |

### 4.15. Client documentation: docs/

Contains this folder/file reference in a version suited to repository reading and another suited to sharing or printing.


| File | What it does | When it is used |
| --- | --- | --- |
| [CLIENT_CODEBASE_GUIDE.md](../docs/CLIENT_CODEBASE_GUIDE.md) | Editable Markdown source of the folder structure, file explanations, runtime trace and generated-file reference. | Read in GitHub or a text editor; update it when the client codebase changes. |
| [INFORSURE_Client_Guide.docx](../docs/INFORSURE_Client_Guide.docx) | Formatted Word copy of the same guide with headings, folder tree, explanatory tables and page numbering. | Share with the client or print. Regenerate it after substantive Markdown changes. |

### 4.16. English collection template: docs/templates/

Contains an empty workbook the client can populate with reviewed English claims before exporting the claims sheet to CSV.


| File | What it does | When it is used |
| --- | --- | --- |
| [english_claims_template.xlsx](../docs/templates/english_claims_template.xlsx) | Blank claims sheet matching the ten original corpus columns, plus five recommended provenance fields. Includes column_guide and collection_log sheets, label/language dropdowns and frozen headers. It contains no training samples. | Use for collection and review; export only the claims sheet as CSV UTF-8 before cleaning/training. |


## 5. Files and folders created after installation or training

These paths may be missing immediately after cloning. Their absence from the source tree is expected until the relevant setup, runtime or training step creates them.


| Path | What creates it / what it contains | Purpose |
| --- | --- | --- |
| .venv/ | Created by setup-demo.ps1. Holds the local Python interpreter and installed dependencies. | Used by setup/start scripts; kept out of Git. |
| .cache/huggingface/ | Local downloads of embedding/NLI models and pretrained training assets when HF_HOME points here. | Avoids downloading them again; needed for cached offline loading. |
| .cache/downloads/ | Used by model_download.py when downloading a release ZIP itself; may contain a temporary .part download. | Installer cache; a manually supplied root ZIP does not have to be cached here. |
| data/runtime/ | Created during handoff preparation to hold the working client database. | Keeps day-to-day feedback separate from the shipped source snapshot. |
| data/runtime/infosure.db | Working SQLite copy used by start-demo.ps1 for evidence queries and feedback inserts. | Preserve/back up it when client feedback or evidence has changed. Restarting does not reset it. |
| models/v0.2-xlmr-pubhealth-en-exp/model.safetensors | Installed from the supplied release ZIP after checksum verification. | The actual learned classifier weights required by live inference. |
| v0.2-xlmr-pubhealth-en-exp-weights.zip | Optional copy placed beside README, or supplied through -ModelArchive. Contains the trained weights. | Private release assets can be downloaded in an authorized browser and transferred this way. |
| training/runs/<model-version>/ | Created by training.run for a new training run. | Contains that run's report.json and checkpoint/; not part of this delivered source history. |
| training/runs/<model-version>/report.json | Records split sizes, selected candidate, validation/test metrics, source counts and gate result. | Read after a future training run; generated evaluation record. |
| training/runs/<model-version>/checkpoint/ | Saved best-validation transformer weights, tokenizer, architecture and temperature for that run. | Training intermediate/cache. Reusing the same run checkpoint can load it rather than retrain it. |
| data/training/splits/<dataset-version>/ | Created by training.run, containing train.csv, val.csv and test.csv. | Training data partition outputs; not live evidence or manually curated source data. |
| models/<new-model-version>/ | Created by training.package when a selected model is packaged. | Contains the new model artifact and metadata. A failed gate is packaged only with explicit --save-candidate and cannot be deployed through the gate-checked CLI. |
| data/training/<new-dataset-version>.csv and .report.json | Created by the cleaning or reviewed-feedback dataset tool when explicitly run. | New labeled English data and a preparation report. Newly generated datasets need deliberate review before sharing/training. |
| __pycache__/ and *.pyc | Automatically created by Python to cache imported bytecode. | Runtime implementation cache; not source or model weights. |
| SQLite journal/WAL/SHM sidecar files | May be created alongside a DB according to SQLite transaction/journal behavior. | Managed by SQLite; not separate evidence datasets. |


A Git clone may also contain a hidden .git/ folder holding version history and remote configuration. A downloaded source ZIP normally has no .git/. This folder belongs to Git, not to the application runtime.

## 6. Which files run for a client action

### 6.1. Highlighted or pasted text

1. content.js forwards the user's page selection to sidepanel.js; typed/pasted text is already in the panel.
2. sidepanel.js sends POST /analyze to main.py when the user checks the text.
3. main.py validates the request with schemas.py and calls pipeline/run.py.
4. run.py calls stages.py. lexicon.py reads lexicon.xlsx to check health relevance and exclude question/opinion phrasing.
5. stages.py selects the first checkable assertion for text mode. model_store.py loads the selected package; transformer_classifier.py uses its tokenizer, model.safetensors and temperature.
6. evidence_index.py embeds the claim through embeddings.py, searches vectors.npy, uses index.json to identify matches, and reads Validated passages/source details from SQLite.
7. nli.py scores each passage against the claim. verification.py aggregates those scores; decision.py combines the evidence verdict with the classifier label.
8. main.py returns a structured AnalyzeResponse. sidepanel.js displays the assessment, classifier estimate, evidence and source links.

Requests may finish early when the text is outside the health domain or has no verifiable health claim. A scope value of verified means the claim reached the analysis flow; it does not by itself mean that the claim was proven true.

### 6.2. Image input

1. sidepanel.js receives an uploaded, pasted or dropped image and sends POST /ocr.
2. main.py calls ocr.py, which returns extracted text and recognition information.
3. The panel sends the extracted text for analysis with source=image. The OCR review controls allow the user to edit/recheck the text.
4. The same analysis stages run. Image text is treated as one claim, capped at 800 characters by default, and the response reports truncation if applicable.

The server processes image bytes in memory; it does not persist the image file. Text can be retained separately when the user submits feedback or the panel keeps a recent check.

### 6.3. Feedback and later training

1. sidepanel.js sends POST /feedback with the claim, displayed prediction/evidence result, user response and model version.
2. main.py inserts a Pending record through db.py into the selected working DB.
3. A person later uses review.py to validate/reject it and provide a label if accepted.
4. dataset_version.py can build a new versioned dataset from the base CSV and validated feedback.
5. After English/source review and a suitable config update, training/run.py can train a new model using split.py, transformer.py, evaluate.py and package.py.

There is no automatic retraining after a feedback click. Merely creating or packaging a model does not switch the active version.

## 7. Key settings and how they connect


| Setting / source | Where it is used | Current behavior |
| --- | --- | --- |
| models/active.json | setup-demo.ps1 and start-demo.ps1 | Selects v0.2-xlmr-pubhealth-en-exp by default. |
| start-demo.ps1 -ModelVersion | Client start script | Overrides the active.json selection for that session and sets INFOSURE_MODEL_VERSION. |
| INFOSURE_MODEL_VERSION | model_store.py and handoff.py | Explicit version selection takes priority over DB Deployed lookup. |
| model_versions.deployment_status | model_store.py when no environment override is set | Only a Deployed row is selected implicitly. The supplied model remains Candidate but is explicitly selected by the scripts. |
| INFOSURE_DB | config.py / database modules | The scripts set data/runtime/infosure.db. Without an override, config.py defaults to data/infosure.db. |
| INFOSURE_MODELS_DIR / INFOSURE_INDEX_DIR | config.py | Optional overrides for model and evidence-index directories; defaults are models/ and data/index/. |
| HF_HOME | Hugging Face model download/loading | The scripts point it to .cache/huggingface/ in the project. |
| INFOSURE_TOP_K / INFOSURE_SIMILARITY_MIN | Evidence retrieval | Defaults: up to 3 passages with cosine similarity at least 0.40. |
| INFOSURE_NLI_MIN_CONFIDENCE | Evidence verdict aggregation | Default threshold 0.70. Retrieval/NLI thresholds require evaluation on labeled claim-evidence data. |
| IMAGE_CLAIM_MAX_CHARS / OCR_MAX_BYTES | Backend config; matching interface limits in sidepanel.js | Defaults: 800 characters per image claim and 5 MiB image upload. Coordinate frontend/backend changes. |
| API_BASE in extension/sidepanel.js | Extension HTTP requests | http://127.0.0.1:8000; must match the backend address used by the scripts. |


Directly starting Uvicorn does not automatically read models/active.json or reproduce all start-demo.ps1 environment settings. The start script is the documented client entry point.

## 8. Where to look when making a change


| Client/developer task | Start with | Related files |
| --- | --- | --- |
| Change interface wording, behavior or result display | extension/sidepanel.js | sidepanel.html for structure; sidepanel.css for styling. |
| Change selection capture | extension/content.js | sidepanel.js for the selection connection and request. |
| Change API fields or request validation | backend/app/schemas.py | main.py and the corresponding sidepanel.js request/rendering code. |
| Adjust health, question or opinion phrases | data/lexicon/lexicon.xlsx | pipeline/lexicon.py; restart backend after edits. |
| Understand or change stage order | backend/app/pipeline/run.py | stages.py and schemas.py. |
| Change trained classifier selection | models/active.json or start-demo.ps1 -ModelVersion | model_store.py, the packaged model folder and model registration in the selected database. |
| Add or review evidence | backend/app/ingest.py and review.py | Runtime DB, evidence_index.py and data/index/; rebuild the matching index. |
| Change final assessment wording/logic | pipeline/decision.py and schemas.py | verification.py for evidence aggregation; sidepanel.js for translated/display text. |
| Continue English training | training/configs/english_xlmr.json and training/run.py | data/training/pubhealth_v1.csv, transformer.py, split.py, evaluate.py and package.py. |
| Track which data/model produced a result | Response model_version and model metadata.json | SQLite model_versions/dataset_versions and the dataset checksum. |


## 9. Handover boundaries and maintenance notes

- The supplied classifier is XLM-RoBERTa fine-tuned on English PUBHEALTH. Its multilingual pretrained architecture and the interface's EN/TL display option do not establish Filipino-language prediction performance.
- The recorded English test split accuracy is 82.70%, with macro-F1 0.8195. These are experimental split results; classification can still disagree with valid evidence. Model confidence is not factual certainty.
- The health/question/opinion stage uses transparent lexicon rules. It is not a separately trained scope classifier.
- Missing or conflicting usable evidence returns Insufficient Evidence. It is not automatically treated as misinformation.
- Keep the database's Validated evidence and the retrieval index synchronized. Maintain the index against the same DB selected for live operation; a source snapshot and an edited runtime DB can diverge.
- The CSV, SQLite evidence and trained weights serve different roles. Editing the CSV does not change an already trained model. Adding evidence does not retrain it. Selecting a different model does not rebuild evidence vectors.
- A private fork does not copy upstream release assets. A client needs authorized access to the model release or a transferred copy of the verified ZIP.
- The author's old experiment outputs, alternative trial datasets, comparison scripts, translation work, test suite and internal thesis documents are outside this client guide and handoff.

## 10. Suggested reading order

1. README.md for installation and operation.
2. This guide's folder tree and the folder relevant to your task.
3. extension/sidepanel.js, backend/app/main.py and backend/app/pipeline/run.py to follow a request.
4. stages.py and the specific processing module you need to understand.
5. metadata.json within the supplied version folder, then training/run.py and the English config if continuing training.

The actual metadata path is models/v0.2-xlmr-pubhealth-en-exp/metadata.json. Examples containing <model-version> or <dataset-version> are placeholders for future versions, not literal folder names.

## 11. Client continuation: simple command-line instructions

Use PowerShell in the client project root, where README.md and setup-demo.ps1 are located. The commands in Sections 11-21 are the normal workflow. Copy one command at a time, wait for it to finish, and read its message before continuing. Stop if a command reports an error.

Each PowerShell box below is something to run in the terminal. Boxes marked JSON show configuration to edit in a file; do not paste those into PowerShell. Longer optional automation scripts are separated into the Advanced appendices at the end.

The Python commands start with .\.venv\Scripts\python.exe. This uses the environment installed by setup and needs no $clientPython variable or argument-array definition. Use the example filenames consistently, or replace them consistently with your own new version names. The input data must exist before running a command that reads it.

### 11.1. Install and run the received system

Check the required Python version:

```powershell
py -3.13 --version
```

For a private repository, download the supplied model ZIP in an authorized GitHub browser session and put it beside README.md. Install runtime and training dependencies:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-demo.ps1 -IncludeTraining
```

If setup was already completed without training dependencies, install just those:

```powershell
.\.venv\Scripts\python.exe -m pip install -r training/requirements.txt
```

Start the backend and keep that window open:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1
```

Wait for InforSure models ready. Open http://127.0.0.1:8000/status in your browser and check warming=false and error=null as well as ready=true. Load extension/ in Chrome using Developer mode -> Load unpacked, then check a claim. Record that the received model version is v0.2-xlmr-pubhealth-en-exp before changing it.

To inspect the exact returned model_version, open http://127.0.0.1:8000/docs, expand POST /analyze, choose Try it out, enter a health claim in the request and Execute. The response identifies the model that actually processed it. This checks selection and function; it does not measure accuracy.

### 11.2. Before changing data or training

Stop the backend with Ctrl+C in its terminal. Close other DB maintenance commands. In File Explorer, make a dated backup folder outside the files you will edit, and copy these items into it: data/infosure.db, data/runtime/infosure.db if it exists, models/active.json and data/index/. Keep the supplied model folder and original English CSV unchanged.

These file copies assume there are no active DB writers. Write new versioned files for collected data, cleaned data, configs and models. An optional scripted backup is in Advanced appendix F.


## 12. Collect and review an English dataset

### 12.1. What to look for

Collect English, health-related factual claims with traceable labels and source information. Prefer an existing labeled dataset with a documented annotation process, or a manually reviewed collection of fact-checked health claims. A raw article is not automatically a labeled training sample.

The current corpus comes from PUBHEALTH. Its [upstream data documentation](https://github.com/neemakot/Health-Fact-Checking/blob/master/data/README.md) describes the available downloads and source fields. The [Imperial College dataset card](https://huggingface.co/datasets/ImperialCollegeLondon/health_fact) documents English claims and four original labels. These are reference entry points for understanding and checking provenance; adding an already included PUBHEALTH claim again does not provide a genuinely new sample.

For another source, inspect its dataset card, annotation instructions, version/date, download files and reuse terms before adopting it. Record the exact download page or fact-check URL and the original label. The client handoff does not include an automatic web scraper or a universal importer for every external dataset format; download and inspect the source, then map its fields into the workbook schema below.

Use this review sequence for every batch:

1. Preserve the downloaded source file separately, with its source name, version, collection date, URL and reuse/license note recorded in the workbook's collection_log sheet.
2. Identify the actual claim text and the label that applies to that exact claim. Do not put an entire fact-check article or its explanatory answer in the text field.
3. Keep health claims that make a checkable assertion. Hold aside questions, personal opinions, unclear claims, unrelated politics or other non-health topics.
4. Verify that the claim itself is English. This continuation workflow does not translate claims or use Filipino/Taglish training batches.
5. Have a reviewer check the label against the source's judgment and explanation. Record disagreements for resolution rather than guessing a class.
6. Group repeated claims, paraphrases, reposts and closely related versions of the same claim together before splitting. Inspect overlap with the supplied PUBHEALTH corpus as well as within the new batch.
7. Inspect the distribution of labels and topics. Collect both classes and varied sources; avoid a dataset where wording or publisher style trivially reveals the label.

The cleaning script removes certain invalid rows and duplicates. It does not judge truth, determine health relevance, verify labels, or independently establish that a sentence is English. Those are collection/review responsibilities.

### 12.2. Map source labels carefully

| Original judgment | Training label / action | Review requirement |
| --- | --- | --- |
| Clearly true / supported claim | Reliable | Confirm that the judgment applies to the exact claim and context. |
| Clearly false / refuted claim | Misinformation | Confirm that the wording has not reversed or weakened the source claim. |
| Mixture, partly true, unproven, ambiguous or missing label | Hold outside the two-class training CSV | Resolve through a documented annotation policy; do not force a binary label. |
| No existing label; reviewer has checked the claim and evidence | A reviewer-approved Reliable or Misinformation label | Keep reviewer and evidence/source references; resolve uncertainty before inclusion. |

When importing numeric labels, inspect that source's label names first. The original PUBHEALTH mapping used by this project was 2 = true -> Reliable and 0 = false -> Misinformation, with other labels excluded. Another dataset can use different numeric meanings. A claim's source being reputable is not, by itself, a label for the claim.

### 12.3. Suggested batch naming

Use new names for each collection and revision. The worked commands below use one consistent example:

| Item | Example name | Purpose |
| --- | --- | --- |
| Raw collected English batch | english_batch_v1.csv | Reviewed source rows exported from Excel; preserve unchanged after export. |
| Origin value on each new row | client/english/batch_v1 | Declares this reviewed batch's provenance, not an existing required folder. |
| Cleaned new batch | english_batch_v1_clean.csv | New batch after cleaning. |
| Merged input | english_v2_merged.csv | Existing English corpus plus cleaned new rows, before global deduplication. |
| Final training dataset/version | english_v2.csv | Globally cleaned corpus used for this run. |
| Training config | english_v2.json | Allows the approved origins and groups related claims. |
| New model version | v0.3-en | A new packaged model; change the version for subsequent runs. |

These are worked example names for files you will create. No such new data or training run is supplied as a completed result in this handoff.

## 13. Prepare Excel in the correct format

### 13.1. Use the supplied workbook template

Open [english_claims_template.xlsx](templates/english_claims_template.xlsx). It contains:

- claims: the rows to export for training; row 1 contains the column names.
- column_guide: explains each column and accepted values.
- collection_log: a separate batch-level record for source URL/version, collection date, license and review notes. Do not export this sheet as the training CSV.

The first ten columns match data/training/pubhealth_v1.csv. The template adds five recommended provenance columns; the cleaner preserves additional columns, while the classifier trains from text and label.

| Column | What to enter | Example / rule |
| --- | --- | --- |
| text | The exact English factual health claim | One claim per row. Do not include the reviewer answer, verdict prefix or full article. |
| label | The final reviewed class | Exactly Reliable or Misinformation, including capitalization. |
| source | Source dataset/publisher name | The real source name, not a fabricated citation. |
| health_topic | Health category | For example nutrition, infectious disease or vaccination. |
| unit | Sample type | claim |
| label_status | How the label was obtained | dataset_label for retained documented dataset labels; validated_by_reviewer for human-approved labels. |
| origin | Reviewed collection identifier | client/english/batch_v1 for all rows in this worked batch. |
| group | Shared identifier for related claim variants | Use the same group for the same claim family even across reposts/paraphrases. |
| fact_checker | Source fact-checker or author attribution | Retain available source attribution; do not invent a person. |
| language | Reviewed claim language | en for this workflow. |
| url | Direct source/fact-check URL | Recommended for each new row; keep source traceability. |
| publication_date | Date of the source judgment | YYYY-MM-DD when available; leave genuinely unavailable values blank. |
| reviewer | Person who reviewed the imported row/label | Record the actual reviewer. |
| review_note | Reasoning or context needed for the label | Keep outside text so the model cannot learn from the answer. |
| license | Source reuse/license reference | Retain documented permission or the applicable source terms. |

Keep headers in row 1 with no title rows above them, no merged cells and no extra totals row. Store IDs, URLs and origin/group values as text. Use final values rather than unresolved formulas. The script requires text and label; the other fields make the collection traceable and let the English-origin guard and group split work as intended.

The dropdowns help with consistent values. They do not validate the truth of the data or guarantee all rows were reviewed. The template contains no training examples and must be populated before use.

### 13.2. Save the claims sheet as CSV

The training tools read CSV, not an Excel .xlsx workbook. In Excel, select claims, choose Save As, then choose CSV UTF-8 (Comma delimited) (*.csv). Keep the original workbook and its collection_log sheet separately.

Create a place for the raw file if the folder does not yet exist:

```powershell
New-Item -ItemType Directory -Path data/raw -Force
```

Save the exported claims sheet as data/raw/english_batch_v1.csv. Do not export column_guide or collection_log as training data. Keep the headers in row 1 and preserve commas/quotes using the CSV export rather than manually renaming an .xlsx file.

If Excel offers a semicolon-separated CSV in your locale, select a comma-separated export. The optional Python workbook conversion is in Advanced appendix A; it is not required when you export correctly from Excel.


## 14. Prepare the updated English training CSV

### 14.1. Clean the newly collected batch

After filling/reviewing the workbook and saving the raw CSV, run this command:

```powershell
.\.venv\Scripts\python.exe -m training.prepare.clean data/raw/english_batch_v1.csv data/training/english_batch_v1_clean.csv
```

This writes a cleaned new batch and a report. Open the report to check removed rows and label counts:

```powershell
notepad data/training/english_batch_v1_clean.report.json
```

The cleaner removes short/invalid rows, exact normalized duplicates and conflicting-label duplicates. It does not verify truth or determine the language; the collection must already be reviewed as English. If an output already exists, choose a new version name rather than replacing the earlier record.

### 14.2. Combine the original and new English rows in Excel

1. Create a new workbook for the combined dataset. Open data/training/pubhealth_v1.csv and copy its columns and rows into the new workbook.
2. Open data/training/english_batch_v1_clean.csv. Append its data rows below the original rows. Keep only one header row. Match columns by their header names, not merely by position.
3. Keep extra provenance columns such as url, reviewer and license if available. Add their headers to the combined sheet and leave unavailable original-row values blank. Preserve text, labels, source, origin and group values.
4. Review related claim groups across both collections. Paraphrases/reposts of the same claim need a shared group; the cleaner does not identify all of them automatically.
5. Export the combined sheet as CSV UTF-8 to data/training/english_v2_merged.csv. Preserve the original PUBHEALTH file unchanged.

Run global cleaning on the combined file so duplicates/conflicts between the old and new rows are handled:

```powershell
.\.venv\Scripts\python.exe -m training.prepare.clean data/training/english_v2_merged.csv data/training/english_v2.csv
```

Open the combined cleaning report and review it before training:

```powershell
notepad data/training/english_v2.report.json
```

The final training file is data/training/english_v2.csv. If you prefer an automated merge rather than Excel, use Advanced appendix B. Both routes retain the original corpus and require global cleaning.

### 14.3. Copy and edit the training config

Use an unused config filename. Copy the supplied English profile:

```powershell
Copy-Item training/configs/english_xlmr.json training/configs/english_v2.json
```

Open the copied file:

```powershell
notepad training/configs/english_v2.json
```

Keep its existing settings. Edit the existing language_by_origin object to allow the reviewed original and new English sources. The following is JSON configuration for the file, not a terminal command:

```json
"language_by_origin": {
  "data/raw/pubhealth": "en",
  "client/english/batch_v1": "en"
}
```

Inside the existing split object, change group_column to group:

```json
"group_column": "group"
```

Replace these fields inside the full copied config; do not replace the entire file with these short fragments. Preserve the commas required by JSON and save as UTF-8 without BOM. Adding an origin is a declaration that the batch has been reviewed, not an automatic language check.

Before training, inspect the CSV for blank text/labels/source/origin/group values, exact labels Reliable/Misinformation, both classes, and related claims sharing a group. Each class needs enough independent groups to fill all three splits. The training runner checks input and split feasibility before training. Advanced appendix D provides an optional data-only preflight.

The updated corpus/grouping creates a new development split. Its score is not an independent direct comparison with the old 82.70% result. Keep additional unseen, reviewed claim families outside the training CSV for a future independent evaluation. The existing runner has no external-holdout command-line option.


## 15. Train and review the updated model

### 15.1. Start a new training run

Use a new model version. Once data/training/english_v2.csv and training/configs/english_v2.json are ready, run:

```powershell
.\.venv\Scripts\python.exe -u -m training.run data/training/english_v2.csv --version v0.3-en --config training/configs/english_v2.json --db data/infosure.db
```

This command validates the data, splits it, fine-tunes XLM-RoBERTa, selects/calibrates on validation, evaluates the test split and packages an accepted model. The dataset version defaults to the CSV name, english_v2. The explicit --db records the new model/dataset in the client source DB so the handoff script can prepare it later; it does not replace evidence rows.

Wait for training to finish. It may need internet to download the base model and can be slow on CPU. The normal copied config starts from FacebookAI/xlm-roberta-base; it is fresh fine-tuning on updated data, not an automatic resume of the supplied trained model or optimizer. Advanced appendix G explains device checks and optional initialization from the existing learned weights.

The configured training settings remain three epochs, batch 4, accumulation 8 and maximum token length 128 unless you deliberately edit them. The gate is macro-F1 >= 0.80 and recall >= 0.70 for each class.

### 15.2. Read the result before selecting it

Open the generated report:

```powershell
notepad training/runs/v0.3-en/report.json
```

Read gate_passed, gate_failures, accuracy, macro_f1, both class recalls, the confusion matrix and error examples. Accuracy alone is not enough. A successful run also has a packaged model folder:

```powershell
Get-ChildItem models/v0.3-en
```

| Training result | What it means | What to do |
| --- | --- | --- |
| Exit code 0; gate_passed is true; package exists | Numerical gate passed and packaging completed | Review behavior, then try the model explicitly. |
| Exit code 2; gate_passed is false | Gate failed; the normal command leaves no new packaged model | Read the report and keep the currently reviewed client model. |
| Error, exception or incomplete output | Run did not finish successfully | Correct the reported problem; do not assume a model is ready. |

A report can exist even if the gate failed and there is no model folder. Do not activate a failed or incomplete package. Passing the numerical gate is also not a guarantee of factual accuracy on new claims.

Expected outputs are training/runs/v0.3-en/report.json, its checkpoint/, data/training/splits/english_v2/, and models/v0.3-en/ if accepted. New registrations are Candidate; training does not change active.json.

Use a fresh version for each genuinely new run. An existing checkpoint can be loaded instead of retraining, and a packaged model version cannot be overwritten by the runner. Preserve old runs and reports.

### 15.3. If only retraining the supplied corpus

No new collected data is needed for this alternative command:

```powershell
.\.venv\Scripts\python.exe -u -m training.run data/training/pubhealth_v1.csv --version v0.3-pubhealth-en --config training/configs/english_xlmr.json --db data/infosure.db
```

This is an alternative run, not an additional mandatory step after Section 15.1. It creates a different model version. Reusing the old test split does not provide an independent new accuracy result.


## 16. Select, verify and roll back the model

### 16.1. Try the accepted replacement for one session

First confirm gate_passed=true in the report and that models/v0.3-en/ contains a completed package. Stop the old backend with Ctrl+C, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -ModelVersion v0.3-en
```

After readiness, use the extension and /docs -> POST /analyze -> Try it out to inspect the returned model_version. It should be v0.3-en. Review representative English text and image inputs, evidence/source links and conflicts. A working request checks functionality; prediction quality needs reviewed examples and evaluation.

The start script explicitly selects a package but does not enforce the numerical gate. Do the report/package review above before using a replacement for the client.

### 16.2. Make the reviewed model the default

Stop the backend. Open the selection file:

```powershell
notepad models/active.json
```

Edit it to the following JSON, then save as UTF-8 without BOM. This is file content, not a command:

```json
{
  "model_version": "v0.3-en"
}
```

Start normally:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1
```

For a persistent rollback, edit model_version back to v0.2-xlmr-pubhealth-en-exp. For a one-session rollback, stop the server and use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -ModelVersion v0.2-xlmr-pubhealth-en-exp
```

Keep the original model folder so rollback remains possible. Gate-checked DB status management is optional and described in Advanced appendix H; updating DB status alone does not override the client scripts' explicit selection.


## 17. Use reviewed client feedback in later training

This optional workflow uses the runtime database created by setup. Select it in your maintenance terminal:

```powershell
$env:INFOSURE_DB = '.\data\runtime\infosure.db'
```

List Pending feedback:

```powershell
.\.venv\Scripts\python.exe -m backend.app.review feedback list --status Pending --limit 20
```

Choose an actual listed ID and review its claim/source. The example 17 below is a placeholder to replace. Choose the correct reviewer label, Reliable or Misinformation, rather than automatically copying the model label:

```powershell
.\.venv\Scripts\python.exe -m backend.app.review feedback set 17 --status Validated --label Reliable --reviewer "Client Reviewer"
```

If unsuitable, use Rejected instead of the validation command:

```powershell
.\.venv\Scripts\python.exe -m backend.app.review feedback set 17 --status Rejected --reviewer "Client Reviewer"
```

These are alternative outcomes, not two commands to apply to the same row in sequence. After reviewing enough English samples, build a new dataset:

```powershell
.\.venv\Scripts\python.exe -m backend.app.dataset_version create english_feedback_v1 --base data/training/english_v2.csv
```

If the continuation corpus has not been created, use data/training/pubhealth_v1.csv as --base instead. The result is data/training/english_feedback_v1.csv and a report, with audit links registered in the selected runtime DB. User clicks do not retrain the model automatically.

Open the new CSV in Excel to review origins such as feedback:17 and confirm English language and labels. Add only the approved exact origins to a new config. Then follow the same validation/training procedure with the new CSV/config and a fresh model version, still using --db data/infosure.db for model registration. Keep the runtime DB because it retains the review/sample audit links.


## 18. Evidence maintenance is a separate optional workflow

Training claims and retrievable evidence are different collections. Adding or training on a CSV does not add evidence to SQLite.

For read-only evidence checks, select the prepared runtime database:

```powershell
$env:INFOSURE_DB = '.\data\runtime\infosure.db'
```

View review-state counts:

```powershell
.\.venv\Scripts\python.exe -m backend.app.review evidence stats
```

Check whether the selected DB matches the index:

```powershell
.\.venv\Scripts\python.exe -m backend.app.review index status
```

Adding or reviewing evidence also requires keeping the source snapshot, runtime DB and shared index synchronized. The full procedure is in Advanced appendix E. Follow it before making evidence changes; importing rows and rebuilding only the runtime index can make the next normal startup reject the older source snapshot. You can skip evidence maintenance when only collecting/training a new classifier.


## 19. Usual command reference

The commands below directly use the installed .venv Python. Run them from the client project root. Read the relevant workflow before commands that write data or change model selection.

| Task | Command | Meaning |
| --- | --- | --- |
| Install runtime plus training dependencies | powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-demo.ps1 -IncludeTraining | First installation, including the optional training dependencies. |
| Start default model | powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 | Uses active.json and the runtime DB. |
| Start cached models offline | powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -Offline | Requires previously downloaded assets. |
| Check readiness | Invoke-RestMethod 'http://127.0.0.1:8000/status' | Check warming=false and error=null as well as ready. |
| Verify supplied local classifier weights | .\.venv\Scripts\python.exe -m backend.app.model_download --verify | Verifies the supplied release weights, not arbitrary later model versions. |
| Show cleaner options | .\.venv\Scripts\python.exe -m training.prepare.clean --help | Confirms input/output arguments. |
| Show training options | .\.venv\Scripts\python.exe -m training.run --help | Lists dataset/version/config/DB/output options. |
| List model registrations | .\.venv\Scripts\python.exe -m backend.app.deploy list | Uses the currently selected INFOSURE_DB or source default; set it explicitly for maintenance. |
| Inspect evidence counts | .\.venv\Scripts\python.exe -m backend.app.review evidence stats | Counts evidence review states in the selected DB. |
| Check retrieval index | .\.venv\Scripts\python.exe -m backend.app.review index status | Shows whether the selected DB's evidence matches the shared index. |
| Inspect pending feedback | .\.venv\Scripts\python.exe -m backend.app.review feedback list --status Pending | Review queue; does not train. |
| Show dataset version tools | .\.venv\Scripts\python.exe -m backend.app.dataset_version --help | Shows create/list operations for reviewed-feedback datasets. |
| Stop backend | Ctrl+C in its server terminal | Releases the port and model memory used by that process. |

## 20. Common problems during continuation

| Symptom | Likely cause | Correct next step |
| --- | --- | --- |
| Missing text or label columns | Wrong Excel sheet, title row, header spelling or delimiter | Export claims as CSV UTF-8 with exact lowercase headers; inspect the first line. |
| Bad labels or many invalid-label removals | Capitalization/spaces, numeric IDs or unsupported original labels | Map reviewed source labels to exactly Reliable/Misinformation before cleaning. |
| Unknown English source origin | The config still allows only PUBHEALTH, or a batch origin is mistyped | Review the batch language/provenance and add its exact origin to a copied config. |
| Preflight finds blank groups or split lacks a class | Missing group metadata or too few distinct label groups | Curate groups and collect adequate reviewed examples for both classes. |
| Empty cleaned file | Empty template or rows dropped by validation | Populate/review data and inspect the cleaning report before training. |
| File/model version already exists | An earlier output or completed package uses the chosen name | Preserve the earlier run and choose a new version; do not overwrite the supplied model. |
| Config JSON fails to load | Invalid JSON or a UTF-8 BOM from an editor/PowerShell export | Validate the JSON and save UTF-8 without BOM; use UTF-8 without BOM in your editor; optional config automation is in Advanced appendix C. |
| Training is slow and CUDA available is false | CPU-only PyTorch or unavailable compatible GPU | CPU is valid; review hardware/driver/build compatibility if GPU training is intended. |
| CUDA out of memory | Another model/server uses VRAM or the batch is too large | Stop the backend; use a new reviewed config/run with smaller batch/evaluation batch and appropriate accumulation. |
| Gate failed, no new model folder | The standard training command deliberately did not package the failed model | Read gate_failures and per-class results; keep the current active version. |
| Backend still returns the old model version | Old server process or unchanged script default | Stop it, select the new packaged version explicitly, restart, and inspect /analyze model_version. |
| No deployed model with direct Uvicorn command | It lacks the script's explicit version environment and runtime settings | Use start-demo.ps1 or deliberately reproduce its settings. |
| Source snapshot reports stale index after evidence maintenance | Runtime-only evidence changes changed the shared index | Follow Advanced appendix E to synchronize the maintained snapshot and runtime state. |
| Private model ZIP download returns 404 | Anonymous installer request cannot access the private release | Download it in an authorized GitHub browser session; place it beside README or use -ModelArchive. |

## 21. Record and hand over the next version

For each future run, retain the reviewed workbook and collection log, raw batch, cleaning reports, final CSV/checksum, exact config, model/run version, split outputs, report.json, packaged artifacts and review notes. Record who approved the labels and which model the client scripts select. Keep newly reserved independent evaluation data out of the training CSV.

The shipped .gitignore intentionally excludes newly generated training CSVs, run folders, additional model directories, runtime DBs and downloaded ZIPs. Therefore git add . alone will not publish a later model/dataset. For a deliberate future handoff, review and explicitly include the selected source CSV/config/metadata, publish its large weights as a versioned release asset, and update active.json/download.json and the relevant ignore exceptions. A new release must have its own measured file sizes/checksums; do not copy the old values.

Maintain evidence snapshot/index compatibility and review whether client feedback should be distributed before including an updated DB. Update README and this Word guide for the chosen version. The example commands in this guide prepare a workflow; they have not collected new real claims, trained a new model, deployed a replacement, or changed the supplied system automatically.

## Advanced appendices: optional automation scripts

The main instructions above use ordinary terminal commands and Excel/editor steps. The blocks in these appendices are longer automation scripts for maintainers who prefer them. They are not additional mandatory steps after completing the equivalent main workflow.

Some blocks are PowerShell scripts containing embedded Python code between @' and '@. Copy the entire block only when using that named automation workflow. Do not run a Python fragment directly as a PowerShell command. Stop if a script reports an error.

## Advanced appendix A. Convert a populated Excel workbook

Alternative to Excel Save As. Save the populated claims workbook as data/raw/english_batch_v1.xlsx first. This exports only claims; it refuses to overwrite an existing CSV.

```powershell
# Save your populated workbook at this path first.
$workbookPath = 'data\raw\english_batch_v1.xlsx'
$rawCsvPath = 'data\raw\english_batch_v1.csv'
if (Test-Path -LiteralPath $rawCsvPath) {
    throw 'The CSV already exists. Preserve it or choose a new batch version.'
}
@'
from pathlib import Path
import pandas as pd
folder = Path('data/raw')
workbook = folder / 'english_batch_v1.xlsx'
output = folder / 'english_batch_v1.csv'
if output.exists():
    raise FileExistsError(output)
df = pd.read_excel(workbook, sheet_name='claims', dtype=str)
df.to_csv(output, index=False, encoding='utf-8')
print(f'Exported {len(df)} rows to {output}')
'@ | .\.venv\Scripts\python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Workbook export failed.' }
```

## Advanced appendix B. Merge CSV files automatically

Alternative to combining rows in Excel. Run after cleaning the new batch and before the global-cleaning command in Section 14.2. It retains the union of columns and preserves both source files.

```powershell
@'
from pathlib import Path
import pandas as pd
output = Path('data/training/english_v2_merged.csv')
if output.exists():
    raise FileExistsError(f'Choose a new version: {output}')
base = pd.read_csv('data/training/pubhealth_v1.csv', dtype=str)
new = pd.read_csv('data/training/english_batch_v1_clean.csv', dtype=str)
merged = pd.concat([base, new], ignore_index=True, sort=False)
merged.to_csv(output, index=False, encoding='utf-8')
print(f'Base={len(base)}; new={len(new)}; merged={len(merged)}')
'@ | .\.venv\Scripts\python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Dataset combination failed.' }
```

## Advanced appendix C. Create the config automatically

Alternative to the copy/edit steps in Section 14.3. Only use this for the reviewed origins shown; change them deliberately for a different batch. Do not run it after already creating the same config filename.

```powershell
$newConfigPath = Join-Path (Get-Location) `
    'training\configs\english_v2.json'
if (Test-Path -LiteralPath $newConfigPath) {
    throw 'This config version already exists. Review it or choose a new version.'
}
$continuationConfig = Get-Content 'training\configs\english_xlmr.json' `
    -Raw | ConvertFrom-Json
$continuationConfig.language_by_origin = [ordered]@{
    'data/raw/pubhealth' = 'en'
    'client/english/batch_v1' = 'en'
}
$continuationConfig.split.group_column = 'group'
$configJson = $continuationConfig | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText(
    $newConfigPath, $configJson, [System.Text.UTF8Encoding]::new($false)
)
```

## Advanced appendix D. Check data without training

Optional technical preflight after the combined CSV and new config are ready. It exercises the actual loader, language/origin guard and group splitter without loading or training XLM-RoBERTa.

```powershell
@'
import json
from pathlib import Path
from training.run import load_dataset, validate_language
from training.split import split_dataset
dataset = Path('data/training/english_v2.csv')
config = json.loads(Path('training/configs/english_v2.json').read_text())
df = load_dataset(dataset)
validate_language(df, config)
assert len(df) > 0, 'The dataset is empty'
assert set(df['label']) == {'Reliable', 'Misinformation'}, 'Need both classes'
for column in ('source', 'origin', 'group'):
    assert column in df, f'Missing column: {column}'
    assert df[column].notna().all(), f'Blank {column} values'
    assert df[column].astype(str).str.strip().ne('').all(), column
parts = split_dataset(df, config['split'], config['seed'], 'group')
print('Total:', len(df))
print('Labels:', df['label'].value_counts().to_dict())
print('Origins:', df['origin'].value_counts().to_dict())
for name, part in parts.items():
    print(name, len(part), part['label'].value_counts().to_dict())
'@ | .\.venv\Scripts\python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. Fix the data before training.' }
```

## Advanced appendix E. Full evidence maintenance

Evidence is the text that the running system retrieves to support or contradict claims. A label in the training CSV does not add anything to the evidence repository.

Prepare a separate CSV UTF-8 with required columns source, url and text. Here text is a sourced evidence passage/article content, not necessarily a short labeled claim. Optional columns are title, publication_date, topic, normalized_claim and license. The training template and evidence-import CSV have different schemas.

With the backend and other DB writers stopped, back up the source and runtime DBs and the two data/index/ files before this maintenance session. Confirm the runtime DB was already created by setup. Set the runtime DB explicitly:

```powershell
$env:INFOSURE_DB = Join-Path (Get-Location) 'data\runtime\infosure.db'
if (-not (Test-Path -LiteralPath $env:INFOSURE_DB)) {
    throw 'Run setup-demo.ps1 to prepare the runtime database first.'
}
.\.venv\Scripts\python.exe -m backend.app.ingest 'data/raw/client_evidence_v1.csv'
if ($LASTEXITCODE -ne 0) { throw 'Evidence import failed.' }
.\.venv\Scripts\python.exe -m backend.app.review evidence list --status Pending --limit 20
.\.venv\Scripts\python.exe -m backend.app.review evidence review `
    --reviewer 'Client Reviewer' --limit 20
```

During the interactive review, inspect the source and passage before choosing a status. Imported rows start Pending and are not retrievable until Validated. The review command normally rebuilds the index. Check it or rebuild explicitly if needed:

```powershell
.\.venv\Scripts\python.exe -m backend.app.review evidence stats
.\.venv\Scripts\python.exe -m backend.app.review index status
.\.venv\Scripts\python.exe -m backend.app.review index build
if ($LASTEXITCODE -ne 0) { throw 'Evidence index rebuild failed.' }
```

Important current handoff behavior: source and runtime databases share data/index/, and handoff preparation checks that index against both databases. After changing runtime evidence and rebuilding its index, the shipped source snapshot must be refreshed to the same evidence state before the next normal start. Otherwise startup can reject the index as stale for the older source snapshot.

After backing up both DBs and stopping all writers, the following SQLite backup refreshes the entire client source snapshot from the maintained runtime DB. It copies all tables, including client feedback and model registrations, not only evidence:

```powershell
@'
import sqlite3
from contextlib import closing
from pathlib import Path
runtime = Path('data/runtime/infosure.db')
snapshot = Path('data/infosure.db')
if not runtime.is_file() or not snapshot.is_file():
    raise FileNotFoundError('Both prepared client databases must exist')
if runtime.resolve() == snapshot.resolve():
    raise ValueError('Runtime and snapshot must be different paths')
with closing(sqlite3.connect(runtime.resolve().as_uri() + '?mode=ro', uri=True)) as src:
    assert src.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    with closing(sqlite3.connect(snapshot.resolve().as_uri() + '?mode=ro', uri=True)) as old:
        for table, column in (
            ('model_versions', 'model_version'),
            ('dataset_versions', 'dataset_version'),
        ):
            previous = {r[0] for r in old.execute(f'SELECT {column} FROM {table}')}
            current = {r[0] for r in src.execute(f'SELECT {column} FROM {table}')}
            if not previous <= current:
                raise ValueError(f'Reconcile source-only {table} before refresh')
    with closing(sqlite3.connect(snapshot)) as dst:
        src.backup(dst)
        assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print('Refreshed client snapshot from maintained runtime database')
'@ | .\.venv\Scripts\python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Snapshot refresh failed.' }
```

If you have newly trained models registered only in the source DB, first prepare each intended version into the runtime DB while the old evidence/index still match, or preserve and reconcile those registrations before this whole-DB refresh. The snapshot refresh replaces the source DB contents with the runtime DB contents. Review the refreshed snapshot before committing it because it now includes client feedback. Restart using start-demo.ps1 after the databases and index agree.

## Advanced appendix F. Dated backup script

Alternative to copying files in File Explorer. Stop the backend and all DB writers first. Keep an additional backup of data/index/ before evidence changes.

```powershell
$backupStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupFolder = Join-Path (Get-Location) ".cache\backups\$backupStamp"
New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null
Copy-Item 'data\infosure.db' (Join-Path $backupFolder 'source-infosure.db')
Copy-Item 'models\active.json' (Join-Path $backupFolder 'active.json')
if (Test-Path 'data\runtime\infosure.db') {
    Copy-Item 'data\runtime\infosure.db' `
        (Join-Path $backupFolder 'runtime-infosure.db')
}
```

## Advanced appendix G. Device and starting weights

```powershell
.\.venv\Scripts\python.exe -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

CPU training is supported but can be slow. The supplied setup installs CPU PyTorch. On a compatible NVIDIA machine, the development environment used the following CUDA build instead; choose a compatible build for the client's actual hardware/driver rather than installing CUDA blindly:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall torch==2.14.1 `
    --index-url https://download.pytorch.org/whl/cu126
```

The normal config starts from FacebookAI/xlm-roberta-base and fine-tunes on the full updated training partition. It does not automatically resume the supplied trained classifier or an interrupted optimizer state. Initial training may need internet to obtain the base model even when the extension already runs offline.

Optional: to initialize a new run from the supplied classifier's learned weights, deliberately set transformer.model_name in the new config to models/v0.2-xlmr-pubhealth-en-exp before starting. Those local weights must already be installed. The code still creates a new optimizer, new run/version and validation calibration; this is additional fine-tuning, not a resume-from-last-step command.

## Advanced appendix H. DB deployment status

To use the gate-checked deployment CLI against the source DB, select that DB explicitly in a maintenance terminal:

```powershell
$env:INFOSURE_DB = Join-Path (Get-Location) 'data\infosure.db'
.\.venv\Scripts\python.exe -m backend.app.deploy list
.\.venv\Scripts\python.exe -m backend.app.deploy deploy 'v0.3-en'
```

This validates the model artifacts and numerical gate and updates DB deployment status. It does not update active.json, and start-demo.ps1 explicitly sets INFOSURE_MODEL_VERSION, so script selection remains the active.json/-ModelVersion choice. Updating the source deployment state does not automatically copy that state to an existing runtime DB. For the documented client launch flow, keep the explicit selection procedure above as the clear record of which package is used.
