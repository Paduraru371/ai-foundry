$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "code\backend\docker\compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"
$Credentials = Join-Path $ProjectRoot ".credentials"

. (Join-Path $PSScriptRoot "docker-utils.ps1")

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}
if (-not (Test-Path $EnvFile) -or -not (Test-Path $Credentials)) {
    throw ".env or .credentials is missing. Run .\scripts\windows\setup.ps1 first."
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed, but its engine is not running."
}

Remove-LegacyBackendContainers

Write-Host "Starting the RAG API and Qdrant with Docker Compose..."
Write-Host "API:     http://localhost:7799"
Write-Host "Swagger: http://localhost:7799/docs"
Write-Host "Qdrant:  http://localhost:7833/dashboard"
Write-Host ""

$ComposeArgs = @(
    "compose",
    "--env-file", $Credentials,
    "--env-file", $EnvFile,
    "-f", $ComposeFile
)
& docker @ComposeArgs up --build
exit $LASTEXITCODE
