# INFORSURE-client

Documentation: [Folder and file guide](docs/CLIENT_CODEBASE_GUIDE.md) | [Full Word guide v1.4](docs/INFORSURE_Client_Guide.docx)

InforSure runs a Chrome extension, a local FastAPI backend, a trained English XLM-RoBERTa claim classifier, and evidence retrieval from SQLite. The saved model is ready to use; training is optional. This repository also includes the English training dataset and pipeline for continued development.

## Run on Windows

1. Install **Python 3.13, 64-bit**, including the Python launcher (`py`), and Google Chrome. Confirm `py -3.13 --version`; another default `python` version is fine.
2. Fork and clone this repository, or download and extract its source ZIP. Open PowerShell in that folder.
3. If this repository is private, open its **Releases** page while signed into a GitHub account with access. Download `v0.2-xlmr-pubhealth-en-exp-weights.zip` and place the ZIP in the project root, beside this README. Setup detects it automatically. A private fork needs access to the upstream release, or a manually transferred copy of that ZIP.
4. With internet connected, run setup once:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-demo.ps1
   ```

   Setup creates `.venv`, installs CPU-compatible dependencies, installs and verifies the supplied classifier ZIP (about 1.11 GB), prepares `data/runtime/infosure.db`, and downloads/loads the embedding, NLI and OCR models. If the release is public, setup can download the classifier ZIP automatically. Allow several minutes and several GB of free disk space. An NVIDIA GPU is optional for running the system.

5. Start the backend each time you use the system:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1
   ```

   Wait for **InforSure models ready** and keep this terminal open. `http://127.0.0.1:8000/status` should show `ready: true`, `warming: false`, and `error: null`. API documentation is at `http://127.0.0.1:8000/docs`.

6. Open `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, and choose this repository's `extension` folder. Pin InforSure and open its side panel on a normal webpage.

After the first successful setup, cached models can be used offline:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -Offline
```

Stop with **Ctrl+C**. Restart after changing model selection, backend code or the lexicon. If port 8000 is occupied, stop the other backend before starting this copy.

## Use the extension

- Highlight a health claim on a webpage and click **Check**; typed or pasted text also works.
- In Image mode, upload, paste, drag/drop, or capture an image. Review/edit the OCR text before checking it.
- Both inputs pass through health-domain and question/opinion checks, claim extraction, **XLM-RoBERTa classification**, validated evidence retrieval, NLI evidence verification, and the final assessment with source links.
- Text mode checks the first checkable assertion; image mode treats the extracted text as one claim, capped at 800 characters.
- The classifier estimate (`Reliable` / `Misinformation`) and evidence result (`Supported` / `Contradicted` / `Insufficient Evidence`) are separate. Conflicts remain visible. Missing evidence does not mean a claim is false.
- Feedback is stored as Pending in the runtime DB. It never retrains the model automatically.

The interface's EN/TL display option changes interface wording. It does not translate inputs or establish Filipino-language model accuracy. The supplied training workflow uses English data only.

## Supplied model and data

| Item | Included purpose |
| --- | --- |
| `models/active.json` | Default classifier: `v0.2-xlmr-pubhealth-en-exp` |
| `models/v0.2-xlmr-pubhealth-en-exp/` | XLM-RoBERTa config, tokenizer, temperature calibration and metadata; setup installs the trained `model.safetensors` here |
| `models/download.json` | Fixed model download URL, file sizes and SHA-256 checksums |
| `data/training/pubhealth_v1.csv` | Original cleaned English PUBHEALTH corpus: 4,047 claims, 2,721 Reliable and 1,326 Misinformation |
| `data/infosure.db` | Evidence snapshot and supplied model registration; development feedback has been cleared |
| `data/index/` | Matching retrieval index for the 63 Validated evidence passages |
| `data/lexicon/lexicon.xlsx` | Health, question and opinion checks |
| `backend/`, `extension/` | End-to-end runtime plus evidence ingestion/review and model/dataset management |
| `training/` | English data cleaning, splitting, training, evaluation and model packaging |

The weights are published as a [GitHub release asset](https://github.com/karris041402/INFORSURE-client/releases/tag/english-xlmr-v0.2). A fork or source ZIP contains the download manifest. For a private release, download the model ZIP in an authorized browser and place it beside this README before setup. Forking alone does not copy release assets. If you distribute the project independently, retain access to that asset or host the same ZIP and update `models/download.json`.

You can transfer the release ZIP manually and pass its path to setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-demo.ps1 -ModelArchive 'C:\Downloads\v0.2-xlmr-pubhealth-en-exp-weights.zip'
```

Other dependencies and embedding/NLI/OCR assets still need internet on first setup. With dependencies already installed, ` .\.venv\Scripts\python.exe -m backend.app.model_download --archive 'C:\Downloads\v0.2-xlmr-pubhealth-en-exp-weights.zip'` installs just the classifier.

The supplied classifier was trained for 3 epochs on 2,833 training claims, selected/calibrated on 607 validation claims, and evaluated on 607 test claims. Test accuracy was **82.70%**, macro-F1 **0.8195**, Reliable recall **0.7672**, and Misinformation recall **0.9497**. It passed the configured numeric gate. These are experimental results on this English split, not a guarantee for new claims. The split was used during prior development, so a future independent evaluation should use fresh held-out data.

Known limitation: the classifier can label “Smoking increases the risk of lung cancer.” as Misinformation while retrieved evidence supports it; the system displays a Conflicting assessment. Confidence is a model score, not factual certainty. The evidence layer remains necessary.

The dataset is preserved byte-for-byte from the supplied model's training input (SHA-256 is recorded in metadata). Its old `language` column contains inaccurate automatic tags; the English training profile validates the declared PUBHEALTH source instead. Do not filter that column to reproduce this run. Dataset provenance: [PUBHEALTH by Neema Kotonya and Francesca Toni](https://github.com/neemakot/Health-Fact-Checking), [paper](https://aclanthology.org/2020.emnlp-main.623/). Only true/false labels are mapped to the two classifier classes. Training claims and retrievable evidence are separate collections.

## Continue English training

Install the additional training dependencies after setup:

```powershell
.\.venv\Scripts\python.exe -m pip install -r training/requirements.txt
```

Alternatively, initial setup accepts `-IncludeTraining`. Setup installs CPU PyTorch so the system works on ordinary laptops. CPU training is supported but slow. On a compatible NVIDIA machine, install the appropriate CUDA build before training; the development machine used:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
```

Run training yourself with a **new model version**:

```powershell
.\.venv\Scripts\python.exe -u -m training.run data/training/pubhealth_v1.csv --version v0.3-xlmr-pubhealth-en --config training/configs/english_xlmr.json --db data/infosure.db
```

The config downloads `FacebookAI/xlm-roberta-base` for a fresh run; it does not require the author's local checkpoint cache. It uses seed 42, a 70/15/15 split, batch size 4, accumulation 8, sequence length 128, and 3 epochs. The `url` group column is absent in the supplied CSV, so the inherited split policy groups normalized duplicate text instead. Paraphrases and source overlap need additional curation for a future independent evaluation.

The runner selects the best epoch/candidate using validation data, calibrates on validation, evaluates on test data, checks macro-F1 >= 0.80 and each class recall >= 0.70, and packages a passing model under `models/<new-version>/`. It writes the report to `training/runs/<new-version>/report.json` and registers a Candidate in the specified client DB. It refuses to overwrite an existing model directory. Do not use test results to repeatedly tune and claim an independent test score.

After a new model passes the gate, stop the backend and select it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -ModelVersion v0.3-xlmr-pubhealth-en
```

For a persistent default, change the `model_version` string in `models/active.json` to that packaged version. This is explicit local selection; packaging alone does not mark a model Deployed. The `backend.app.deploy` CLI also supports gate-checked deployment status management. Keep the supplied model until its replacement has been reviewed.

For new English data, retain `text`, `label` (`Reliable` or `Misinformation`), and source provenance. Clean into a new file with `training.prepare.clean`; this cleaner assumes you have already checked that the source is English. Update a copied training config's `language_by_origin` for any approved new sources. The supplied profile intentionally accepts only `data/raw/pubhealth` provenance. Review feedback manually with `backend.app.review` before using `backend.app.dataset_version` to form a new dataset; verify language and labels before training it.

## Maintain evidence and storage

The shipped `data/infosure.db` is a source snapshot. Setup creates a separate runtime DB and preserves existing client feedback on subsequent starts. To review or ingest evidence into the runtime DB, select it in a new PowerShell:

```powershell
$env:INFOSURE_DB = Join-Path (Get-Location) 'data\runtime\infosure.db'
.\.venv\Scripts\python.exe -m backend.app.review evidence stats
.\.venv\Scripts\python.exe -m backend.app.review --help
.\.venv\Scripts\python.exe -m backend.app.ingest --help
```

Only Validated passages are retrieved. Rebuild the index after evidence changes with ` .\.venv\Scripts\python.exe -m backend.app.review index build`. An outdated index causes a clear error rather than retrieving against mismatched data. Source evidence and model files are not overwritten by ordinary claim checks.

This handoff excludes the author's test suite, comparison/ensemble scripts, experiment outputs and old checkpoints, alternative trial datasets, translation code/data, Filipino/Taglish training work, and internal thesis documents. New training runs, generated splits, runtime feedback DBs and downloaded weights stay out of Git by default; publish future model binaries through a versioned release with updated checksums.

## Update an existing SVM installation to XLM-RoBERTa

Use these steps if you already forked, cloned and set up the earlier SVM version. Keep your existing project folder; you do not need to delete it, fork again or clone again.

1. Stop the running backend with **Ctrl+C**.
2. Open your fork on GitHub, then click **Sync fork → Update branch** to get the latest changes from `karris041402/INFORSURE-client`.
3. Open PowerShell in your existing local project folder and run:

   ```powershell
   git pull
   ```

   If Git reports local changes or conflicts, resolve them before continuing; keep any work you need.

4. While signed into a GitHub account with access, open the [upstream model release](https://github.com/karris041402/INFORSURE-client/releases/tag/english-xlmr-v0.2). Download **`v0.2-xlmr-pubhealth-en-exp-weights.zip`** and place it beside `README.md` in your existing project folder. Leave the ZIP unextracted. A fork does not copy the upstream release asset.
5. With internet connected, run the updated setup once:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-demo.ps1
   ```

   Setup reuses the existing `.venv`, checks/updates dependencies and installs the new classifier weights. Valid installed weights and models already in the configured caches are reused; missing or changed assets still need downloading. Existing runtime feedback is preserved. You do not need to retrain the model or download `pubhealth.zip`.

6. Start the backend:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1
   ```

   The terminal should show **`Classifier: v0.2-xlmr-pubhealth-en-exp`**. Wait for **InforSure models ready**, then keep the terminal open. The default in `models/active.json` selects the supplied English XLM-RoBERTa classifier automatically.

7. Open `chrome://extensions` and click **Reload** on the existing InforSure extension.

After this upgrade, run `start-demo.ps1` for normal use. Later updates limited to comments or documentation do not require downloading the model or running setup again.

## Contextual embeddings and SHAP explanations

The supplied XLM-RoBERTa classifier already uses contextual representations. `training/transformer.py` fine-tunes the complete encoder and classification head through `model.parameters()`; the final contextual token states feed the classification head. There is no separate embedding-export step to add before training. MiniLM embeddings in `backend/app/pipeline/embeddings.py` serve evidence retrieval and are a separate part of the flow.

After analyzing a claim, click **Explain prediction** in the result panel. The extension calls `POST /explain` with the exact analyzed claim, model version and predicted label. The endpoint explains the same loaded classifier using **Partition SHAP**, without training another model. This feature requires the XLM-RoBERTa classifier; an older SVM backend cannot provide this explanation.

The panel starts with an English/Tagalog summary of the model score, the words with the strongest estimated influences, and the separate evidence result, including disagreement. Subword tokens are combined into whole words using the original text offsets, so the claim stays readable. Word scores sum their underlying token contributions; they are display groupings, not new whole-word masking experiments. Hover over a word to see its estimated contribution in percentage points. Expand **See SHAP details** for the raw token view and score breakdown. The summary uses the actual SHAP output and evidence status; it does not generate medical reasons or source claims. The baseline is the classifier score with all content tokens masked and boundary tokens kept fixed. Baseline plus the displayed contributions reconstructs the calibrated model score. SHAP is an approximate explanation of that score; evidence verification remains a separate result.

Only tokens within the classifier's existing 128-token limit are explained. A notice identifies truncated inputs. Contributions are calculated on request so normal classification, retrieval and feedback stay responsive. Failed or busy explanation requests leave the original result visible and allow retrying.

### Enable explanations on an existing installation

Stop the backend, update the project files, then install the updated runtime dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Start with `start-demo.ps1`, wait for **InforSure models ready**, and reload InforSure at `chrome://extensions`. The client default already selects `v0.2-xlmr-pubhealth-en-exp`.

This SHAP update does not require downloading the classifier ZIP again, retraining or rebuilding the evidence index if XLM-RoBERTa is already installed. If you still have SVM, complete the preceding SVM-to-XLM-RoBERTa upgrade first.

For laptop tuning, `INFOSURE_SHAP_MAX_EVALS` defaults to 128 and is clamped to 16-512. `INFOSURE_SHAP_BATCH_SIZE` defaults to 4 and is clamped to 1-8. Larger budgets can improve attribution detail but take longer.

References: [XLM-RoBERTa architecture](https://huggingface.co/docs/transformers/model_doc/xlm-roberta), [Partition SHAP](https://shap.readthedocs.io/en/latest/generated/shap.PartitionExplainer.html).
