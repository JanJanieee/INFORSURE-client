# Ihanda ang dependencies, trained model at runtime DB.
param([switch]$IncludeTraining, [string]$ModelArchive)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    # Gamitin ang virtual environment ng project.
    $demoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $demoPython)) {
        & py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.13 (64-bit), then rerun setup.' }
    }
    & $demoPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip update failed.' }
    # CPU build para gumana kahit walang NVIDIA GPU.
    & $demoPython -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed.' }
    & $demoPython -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Runtime dependency installation failed.' }
    # Optional: idagdag ang training libraries.
    if ($IncludeTraining) {
        & $demoPython -m pip install -r training/requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Training dependency installation failed.' }
    }
    # Dito i-cache ang Hugging Face models.
    $env:HF_HOME = Join-Path $PSScriptRoot '.cache\huggingface'
    $env:HF_HUB_OFFLINE = '0'
    # Hanapin ang model ZIP sa project folder.
    if (-not $ModelArchive) {
        $modelManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'models\download.json') -Raw | ConvertFrom-Json
        $localArchive = Join-Path $PSScriptRoot ([System.IO.Path]::GetFileName($modelManifest.url))
        if (Test-Path -LiteralPath $localArchive) { $ModelArchive = $localArchive }
    }
    # I-verify at i-install ang trained model weights.
    $downloadArguments = @('-m', 'backend.app.model_download')
    if ($ModelArchive) { $downloadArguments += @('--archive', $ModelArchive) }
    & $demoPython @downloadArguments
    if ($LASTEXITCODE -ne 0) { throw 'The English classifier could not be installed. Check the connection or provide -ModelArchive.' }
    # Piliin ang model at working DB para sa session.
    $activeModel = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'models\active.json') -Raw | ConvertFrom-Json
    $env:INFOSURE_MODEL_VERSION = $activeModel.model_version
    $env:INFOSURE_DB = Join-Path $PSScriptRoot 'data\runtime\infosure.db'
    # I-check ang assets at i-load ang supporting models.
    & $demoPython -m backend.app.handoff warmup
    if ($LASTEXITCODE -ne 0) { throw 'System preparation failed. Keep internet connected and rerun setup.' }
    Write-Host 'Setup complete. Run .\start-demo.ps1, then load extension/ in Chrome.'
} finally {
    # Ibalik ang dating working folder.
    Pop-Location
}
