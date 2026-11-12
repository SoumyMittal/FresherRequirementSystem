param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$prototypePython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $prototypePython)) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Install it and run start.ps1 again.' }
    & $prototypePython -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.env'))) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '.env.example') -Destination (Join-Path $PSScriptRoot '.env')
}
& $prototypePython -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('dotenv') else 1)"
if ($LASTEXITCODE -ne 0) {
    & $prototypePython -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
Write-Host "Incepta is starting at http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host 'Local prototype with mocked login. Press Ctrl+C to stop.'
& $prototypePython -m uvicorn backend.app:app --host 127.0.0.1 --port $Port
