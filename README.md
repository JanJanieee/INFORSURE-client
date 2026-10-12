# INFORSURE-client: InforSure demo

Run the Chrome extension and Python backend locally with the existing trained model and evidence. No retraining is needed. GitHub hosts the files; the backend runs on the presenter's computer.

## Windows setup

1. Install **Python 3.13, 64-bit**, with the Python launcher (`py`), and Google Chrome.
2. Fork this repository on GitHub if you want your own copy, then clone your fork (or download and extract the repository ZIP).
3. Open PowerShell in the repository folder and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-demo.ps1
   ```

   Keep internet connected during setup. It creates `.venv`, installs CPU-compatible dependencies, copies the included evidence database into `data/runtime/infosure.db`, downloads the embedding/NLI/OCR assets, and checks the real text and image pipelines. The first download can take several minutes. A GPU is optional.

4. Start the backend:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1
   ```

   Keep this terminal open. Wait for `InforSure models ready` in the log. Visit `http://127.0.0.1:8000/status` and check that `warming` is false and `error` is null. `ready` alone does not rule out a loading error.

5. Open `chrome://extensions`, enable **Developer mode**, select **Load unpacked**, and choose the repository's **extension** folder. Pin InforSure and click its icon to open the side panel.

## Present the system

- **Highlighted text:** open a normal webpage, highlight a health claim, then click **Check** in the panel. You can also type or paste the claim.
- **Image:** select the Image tab, accept the first-use notice, then drag/drop, paste, or upload a PNG/JPG/WebP image. The backend reads the text with OCR; review/edit the extracted text when needed.
- Both modes check whether the text is health-related and contains a checkable assertion. Non-health text, questions, and opinions are filtered before classification.
- A checkable claim goes through **Linear SVM classification → validated evidence retrieval → multilingual NLI verification → final assessment**, with the model estimate, evidence result, and source links shown separately. Image text is treated as one claim (up to 800 characters); highlighted text uses the first checkable assertion.
- Feedback is stored as Pending in the runtime database. It does not retrain the classifier.

Try `Smoking increases the risk of lung cancer.` for the full pipeline; `Does smoking cause cancer?` for a question; `I think vaccines are scary.` for an opinion; and `The team won the championship game last night.` for non-health text. These are behavior checks, not a model accuracy evaluation.

## Files included for the demo

| File | Purpose |
| --- | --- |
| `data/infosure.db` | Existing SQLite snapshot, including 63 validated evidence passages, model registration, and existing feedback/review records |
| `data/index/index.json`, `data/index/vectors.npy` | Matching semantic retrieval index |
| `data/lexicon/lexicon.xlsx` | Health terms, question phrases, and opinion phrases |
| `models/v0.0-dev/model.joblib` | Trained Linear SVM and fitted TF-IDF vectorizer |
| `models/v0.0-dev/metadata.json` | Model version, library versions, training details, and metrics |
| `backend/`, `extension/` | API, OCR, classification, retrieval, verification, decision, and browser UI |

This client repository contains only the runnable system. Training code, CSV datasets, experiments, internal documents, and development Git history are excluded. The classifier is the existing **v0.0-dev** artifact, trained on English PUBHEALTH with its acceptance gate disabled; it is not a newly trained XLM-RoBERTa classifier. Retrieval uses multilingual MiniLM, and evidence verification uses multilingual mDeBERTa. An SVM confidence score is not a probability that a claim is true. Missing/weak/conflicting evidence can correctly produce **Insufficient Evidence**.

## Before presenting / troubleshooting

After completing setup, rehearse on the actual presentation laptop. For an offline rehearsal, use `start-demo.ps1 -Offline`; the downloaded models must already be cached on that laptop. Cached assets are local and are not pushed to GitHub.

```powershell
# Verify the included DB, model, lexicon, and matching index.
.\.venv\Scripts\python.exe -m backend.app.handoff check

# Exercise real scope checks, classifier, retrieval, NLI, OCR/image input, and feedback.
$env:HF_HOME = Join-Path $PWD '.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe -m backend.app.handoff smoke
```

- **Backend unavailable:** keep `start-demo.ps1` running on port 8000. API docs: `http://127.0.0.1:8000/docs`.
- **Model download/load failed:** check `/status` for the error, reconnect internet, and rerun setup. If you previously set `HF_HUB_OFFLINE=1`, remove that environment variable before downloading again.
- **Index stale after evidence review:** run `py -m backend.app.review index build` with the same `INFOSURE_DB` used by the backend and the demo virtual environment. The shipped index must match the shipped evidence database; do not replace just one of them.
- **Highlight not captured:** browser pages and the Chrome Web Store block extension scripts. Try a normal webpage or paste the claim.
- **No PowerShell scripts allowed:** `-ExecutionPolicy Bypass` in the commands above applies only to the launched process. It does not change your permanent execution policy.

`data/runtime/`, `.venv/`, `.cache/`, database backups, and database journal/WAL files stay ignored. Startup preserves an existing runtime DB, so the presenter's feedback is retained. The original included `data/infosure.db` remains the shipped snapshot when using these scripts.
