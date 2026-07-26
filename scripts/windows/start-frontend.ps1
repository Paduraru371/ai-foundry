$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FrontendDir = Join-Path $ProjectRoot "code\frontend-admin"

if (-not (Test-Path $VenvPython)) {
    throw "The shared virtual environment is missing. Run .\scripts\windows\setup.ps1 first."
}

Write-Host "Starting the Libra Assist admin console..."
Write-Host "Frontend: http://localhost:7800"
Write-Host ""

& $VenvPython -m uvicorn app.main:app `
    --app-dir $FrontendDir `
    --host 127.0.0.1 `
    --port 7800 `
    --reload
exit $LASTEXITCODE
