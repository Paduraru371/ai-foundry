$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BackendComposeFile = Join-Path $ProjectRoot "code\backend\docker\compose.yml"
$FrontendComposeFile = Join-Path $ProjectRoot "code\frontend-admin\docker\compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"
$Credentials = Join-Path $ProjectRoot ".credentials"

. (Join-Path $PSScriptRoot "docker-utils.ps1")

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

$BackendComposeArgs = @(
    "compose",
    "--env-file", $Credentials,
    "--env-file", $EnvFile,
    "-f", $BackendComposeFile
)
$FrontendComposeArgs = @("compose", "-f", $FrontendComposeFile)

try {
    Write-Host "Starting backend containers..."
    & docker @BackendComposeArgs up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not start the backend."
    }

    Write-Host "Starting the admin frontend container..."
    & docker @FrontendComposeArgs up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not start the admin frontend."
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

    & docker @FrontendComposeArgs logs -f admin
}
finally {
    Write-Host ""
    Write-Host "Stopping frontend and backend containers..."
    & docker @FrontendComposeArgs down
    & docker @BackendComposeArgs down
}
