$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "code\frontend-admin\docker\compose.yml"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is not installed or Docker is not available in PATH."
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed, but its engine is not running."
}

Write-Host "Starting the Libra Assist admin console..."
Write-Host "Frontend: http://localhost:7800"
Write-Host ""

& docker compose -f $ComposeFile up --build
exit $LASTEXITCODE
