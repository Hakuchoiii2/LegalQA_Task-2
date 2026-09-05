$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = Join-Path (Split-Path $ProjectRoot -Parent) ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $Python)) { $Python = "python" }
& $Python (Join-Path $ProjectRoot "scripts\run_inference.py") @args
exit $LASTEXITCODE
