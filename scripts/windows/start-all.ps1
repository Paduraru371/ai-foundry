$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "code\backend\docker\compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"
$Credentials = Join-Path $ProjectRoot ".credentials"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FrontendDir = Join-Path $ProjectRoot "code\frontend-admin"

. (Join-Path $PSScriptRoot "docker-utils.ps1")

if (-not (Test-Path $VenvPython)) {
    throw "The shared virtual environment is missing. Run .\scripts\windows\setup.ps1 first."
}
if (-not (Test-Path $EnvFile) -or -not (Test-Path $Credentials)) {
    throw ".env or .credentials is missing. Run .\scripts\windows\setup.ps1 first."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is not installed or Docker is not available in PATH."
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed, but its engine is not running."
}

Remove-LegacyBackendContainers

$ComposeArgs = @(
    "compose",
    "--env-file", $Credentials,
    "--env-file", $EnvFile,
    "-f", $ComposeFile
)

try {
    Write-Host "Starting backend containers..."
    & docker @ComposeArgs up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not start the backend."
    }

    Write-Host ""
    Write-Host "Services:"
    Write-Host "  Frontend: http://localhost:7800"
    Write-Host "  API:      http://localhost:7799"
    Write-Host "  Swagger:  http://localhost:7799/docs"
    Write-Host "  Qdrant:   http://localhost:7833/dashboard"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services."
    Write-Host ""

    & $VenvPython -m uvicorn app.main:app `
        --app-dir $FrontendDir `
        --host 127.0.0.1 `
        --port 7800 `
        --reload
}
finally {
    Write-Host ""
    Write-Host "Stopping backend containers..."
    & docker @ComposeArgs down
}
