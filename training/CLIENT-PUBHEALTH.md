# Train three models using the existing client handoff

This workflow uses the English PUBHEALTH dataset and training code already included in the client handoff. You do not need another project copy or the original PUBHEALTH archive.

## Update an existing fork

On GitHub, open your fork of `karris041402/INFORSURE-client`, select **Sync fork**, then **Update branch**. Save or commit any local edits before pulling. In PowerShell, open your existing project folder on its `main` branch and run:

```powershell
git pull --ff-only origin main
```

This brings in `training/configs/pubhealth_comparison.json` and this guide. If Git reports divergent branches or conflicts, resolve them before continuing; do not discard local work. A browser source ZIP alone is not a Git checkout and cannot use `git pull`.

## 1. Prepare the existing installation

Finish the handoff's normal setup first. Stop the backend before training to free memory. Open PowerShell in the project root, where `README.md`, `training/` and `.venv/` are located.

Install the training dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r training/requirements.txt
```

The handoff installs CPU PyTorch. SVM and Naive Bayes use the CPU. XLM-RoBERTa also supports CPU training, but it can take much longer. If you have a compatible NVIDIA GPU and driver, the handoff documents this optional CUDA installation:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
```

Check the device before running training:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print('CUDA available:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

If CUDA is unavailable, training uses the CPU. Running `setup-demo.ps1` again installs CPU PyTorch again. Virtual environment activation is optional because every command calls its Python executable directly.

## 2. Train SVM, Naive Bayes and XLM-RoBERTa

Keep internet connected for the first training run. The transformer downloads the public pretrained base model; it does not reuse the supplied fine-tuned classifier.

```powershell
$env:HF_HOME = Join-Path $PWD '.cache\huggingface'
$env:HF_HUB_OFFLINE = '0'
$trainingVersion = 'client-pubhealth-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\.venv\Scripts\python.exe -u -m training.run data/training/pubhealth_v1.csv --version $trainingVersion --config training/configs/pubhealth_comparison.json --db data/runtime/training.db
$trainingExitCode = $LASTEXITCODE
Write-Host "Training version: $trainingVersion; exit code: $trainingExitCode"
```

Every attempt needs a new version, including an interrupted attempt. An existing checkpoint in a reused run directory can be loaded instead of trained again. The timestamp generates a new version without replacing the supplied model. Training registration uses a separate database at `data/runtime/training.db`.

All three candidates use the same seed (42) and train/validation/test split. For the supplied dataset, the expected counts are 2,833 / 607 / 607. The CSV has no `url` column, so the existing splitter groups normalized duplicate text instead. Paraphrases and source overlap still need review for an independent evaluation. The English profile validates source provenance; do not filter the inaccurate automatic `language` tags in the CSV.

SVM and Naive Bayes fit TF-IDF on training text only. XLM-RoBERTa fine-tunes its encoder and classification head for three epochs, then keeps the epoch with the highest validation macro-F1. The configured transformer batch size is 4, with gradient accumulation of 8 and a 128-token limit.

If the transformer reports CUDA out of memory, stop the attempt, reduce `batch_size` and `eval_batch_size` in the comparison config, and use a new version. Record any changed settings with the results.

## 3. Read the actual results

The report is written to `training/runs/<training-version>/report.json`. In the same PowerShell session, display the comparison:

```powershell
$trainingReport = Get-Content -LiteralPath "training/runs/$trainingVersion/report.json" -Raw | ConvertFrom-Json
$trainingReport.validation.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{
        Model = $_.Name
        AccuracyPercent = [math]::Round(100 * $_.Value.accuracy, 2)
        MacroF1 = [math]::Round($_.Value.macro_f1, 4)
    }
} | Format-Table -AutoSize
Write-Host "Selected on validation: $($trainingReport.selected)"
$trainingReport.test | Select-Object n, accuracy, macro_f1
Write-Host "Gate passed: $($trainingReport.gate_passed)"
$trainingReport.gate_failures
```

`svm` means Linear SVM, `nb` means Multinomial Naive Bayes, and `transformer` means XLM-RoBERTa. The validation comparison includes all three models. The `test` section belongs only to the validation-selected winner. The report also includes precision, recall, class metrics, confusion matrices and error examples. The existing runner does not test every candidate or save every trained candidate.

Exit code 0 means the winner passed the gate and was packaged under `models/<training-version>/` as a Candidate. Exit code 2 means it failed the gate; read the report, but no deployment-ready package was created. Exit code 1 means an error; inspect the terminal output. A failed run may not produce a report.

The acceptance gate requires macro-F1 of at least 0.80 and recall of at least 0.70 for each class. Keep these criteria unchanged when reporting whether a run passed. Packaging does not change `models/active.json` or activate the new model. SVM and Naive Bayes do not support the handoff's transformer-only SHAP explanation.

Report the scores produced by the client's run. XLM-RoBERTa is not guaranteed to win, and CPU/GPU runs may differ. This is an experimental reproduction using a split already used during development, not a new independent test or a claim of Filipino/Taglish accuracy. Keep test results out of repeated tuning decisions.
