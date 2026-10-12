param([switch]$Offline)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $demoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Run .\setup-demo.ps1 first.' }
    $env:HF_HOME = Join-Path $PSScriptRoot '.cache\huggingface'
    $env:INFOSURE_MODEL_VERSION = 'v0.0-dev'
    $env:INFOSURE_DB = Join-Path $PSScriptRoot 'data\runtime\infosure.db'
    $env:INFOSURE_WARMUP = '1'
    if ($Offline) { $env:HF_HUB_OFFLINE = '1' }
    & $demoPython -m backend.app.handoff prepare
    if ($LASTEXITCODE -ne 0) { throw 'The demo database, classifier, or evidence index is not ready.' }
    Write-Host 'Demo classifier: v0.0-dev (Linear SVM). Wait for models ready before presenting.'
    Write-Host 'Keep this terminal open. API: http://127.0.0.1:8000/docs'
    & $demoPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw 'The server stopped with an error.' }
} finally {
    Pop-Location
}
