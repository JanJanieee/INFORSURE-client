param([switch]$SkipModelDownload)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $demoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $demoPython)) {
        & py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.13 (64-bit), then rerun setup.' }
    }
    & $demoPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip update failed.' }
    # CPU works on a client laptop without requiring an NVIDIA GPU or CUDA.
    & $demoPython -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed.' }
    & $demoPython -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Runtime dependency installation failed.' }
    $env:HF_HOME = Join-Path $PSScriptRoot '.cache\huggingface'
    & $demoPython -m backend.app.handoff prepare
    if ($LASTEXITCODE -ne 0) { throw 'The shipped demo assets could not be prepared.' }
    if (-not $SkipModelDownload) {
        & $demoPython -m backend.app.handoff warmup
        if ($LASTEXITCODE -ne 0) { throw 'Model download/load failed. Keep internet connected and rerun setup.' }
        & $demoPython -m backend.app.handoff smoke
        if ($LASTEXITCODE -ne 0) { throw 'The full demo flow failed verification.' }
    }
    Write-Host 'Setup complete. Run .\start-demo.ps1, then load extension/ in Chrome.'
} finally {
    Pop-Location
}
