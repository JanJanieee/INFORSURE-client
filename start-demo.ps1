# Simulan ang local backend gamit ang napiling model.
param([switch]$Offline, [string]$ModelVersion)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $demoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Run .\setup-demo.ps1 first.' }
    # Gamitin ang model cache ng project.
    $env:HF_HOME = Join-Path $PSScriptRoot '.cache\huggingface'
    # Parameter muna; active.json kung walang override.
    if (-not $ModelVersion) {
        $activeModel = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'models\active.json') -Raw | ConvertFrom-Json
        $ModelVersion = $activeModel.model_version
    }
    # I-set ang model, working DB at startup warmup.
    $env:INFOSURE_MODEL_VERSION = $ModelVersion
    $env:INFOSURE_DB = Join-Path $PSScriptRoot 'data\runtime\infosure.db'
    $env:INFOSURE_WARMUP = '1'
    # Offline mode: cached models lang.
    if ($Offline) { $env:HF_HUB_OFFLINE = '1' } else { $env:HF_HUB_OFFLINE = '0' }
    # I-check ang assets bago buksan ang API.
    & $demoPython -m backend.app.handoff prepare
    if ($LASTEXITCODE -ne 0) { throw 'The demo database, classifier, or evidence index is not ready.' }
    Write-Host "Classifier: $ModelVersion. Wait for InforSure models ready before checking claims."
    Write-Host 'Keep this terminal open. API: http://127.0.0.1:8000/docs'
    # Dito kumokonekta ang browser extension.
    & $demoPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw 'The server stopped with an error.' }
} finally {
    # Ibalik ang dating working folder.
    Pop-Location
}
