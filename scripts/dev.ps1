<#
.SYNOPSIS
  The teaching lane: the API on your machine, Qdrant and the console in Docker.

.DESCRIPTION
  This is the combination that gives you everything without asking anyone to
  install anything they do not have.

    the API      on your machine, in the repository-root virtual environment.
                 When Azure identity is selected, it can use your `az login`;
                 local/key-based providers do not require Azure CLI.

    the console  in Docker - because students do not have Node installed, and
                 nobody should have to.

    Qdrant       in Docker - because it is a database and that is what containers
                 are for.

  The alternative, everything in Docker, needs a service principal to reach the
  Agent Service (scripts/azure/09-create-service-principal.ps1). If your tenant
  will not let you create one, this lane is the answer: your own login never
  leaves your machine, and the container never needs one.

.EXAMPLE
  ./dev.ps1
  ./dev.ps1 -Port 7801            # if something already holds 7799
  ./dev.ps1 -BindAll              # publish to your network (needed on Docker Engine/Linux)
  ./dev.ps1 -SkipDocker           # containers already up; just run the API
  ./dev.ps1 -Force                # clear a leftover server still holding 7799
#>
param(
    [int]$Port = 7799,
    [switch]$BindAll,
    [switch]$SkipDocker,
    [switch]$NoReload,
    [switch]$Force,             # clear an orphaned local server holding the port
    [ValidateSet("frontend", "frontend-admin")]
    [string]$Frontend = "frontend"
)

$ErrorActionPreference = "Stop"
function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

# --- dependencies -------------------------------------------------------------
Step 0 "Python dependencies"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if ($python) {
        & py -3 -m venv (Join-Path $projectRoot ".venv")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv (Join-Path $projectRoot ".venv")
    } else {
        throw "Python 3.11+ was not found."
    }
}
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt") --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw "Project dependencies could not be installed." }

# --- configuration ------------------------------------------------------------
Step 1 "Configuration"
if (-not (Test-Path ".env")) { throw "No .env here. Start from: copy .env.example .env" }
$envText = Get-Content ".env" -Raw
$usesAzure = (
    $envText -match "(?m)^LLM_PROVIDER=azure\s*$" -or
    $envText -match "(?m)^EMBEDDING_PROVIDER=azure\s*$" -or
    $envText -match "(?m)^AGENT_MODE=foundry\s*$"
)
$usesIdentity = $envText -match "(?m)^AZURE_AI_AUTH=identity\s*$"
Write-Host "    configuration loaded from $projectRoot\.env" -ForegroundColor Green
if ($envText -match "(?m)^QDRANT_URL=(.+)$" -and $Matches[1] -notmatch "localhost") {
    Write-Host "    QDRANT_URL=$($Matches[1]) - expected localhost here; the API is NOT in the compose network" -ForegroundColor Yellow
}

# --- Azure CLI, only when the selected lane needs it --------------------------
Step 2 "Azure identity"
if ($usesAzure -and $usesIdentity) {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        $default = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin"
        if (Test-Path (Join-Path $default "az.cmd")) {
            $env:PATH = "$default;$env:PATH"
            Write-Host "    not on PATH - added $default for this session" -ForegroundColor Yellow
        } else {
            throw "az not found. Install it: https://learn.microsoft.com/cli/azure/install-azure-cli"
        }
    }
    $account = az account show -o json 2>$null | ConvertFrom-Json
    if (-not $account) { throw "Not signed in. Run:  az login" }
    Write-Host "    $($account.user.name)  -  $($account.name)" -ForegroundColor Green
} else {
    Write-Host "    not required for the selected local/key-based configuration"
}

# --- 2 - the port -------------------------------------------------------------
# Two things commonly hold it. A container publishing 7799 - stop the api service.
# Or an orphaned uvicorn: `--reload` runs the server in a CHILD process, and closing
# the terminal can kill the parent while the child keeps the socket. The child's
# command line says `multiprocessing.spawn`, not `uvicorn`, which is why the obvious
# "kill anything called uvicorn" misses it and the port stays busy for no visible
# reason. -Force clears exactly that.
Step 3 "Port $Port"
$busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($busy) {
    $orphans = Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
               Where-Object { $_.CommandLine -match 'multiprocessing\.spawn|uvicorn' }
    if ($orphans -and $Force) {
        $orphans | ForEach-Object {
            Write-Host "    stopping orphaned server $($_.ProcessId)" -ForegroundColor Yellow
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 3
        $busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    }
    if ($busy) {
        Write-Host "    in use." -ForegroundColor Yellow
        if ($orphans) {
            Write-Host "    an orphaned local server is holding it - re-run with -Force" -ForegroundColor Yellow
        } else {
            Write-Host "    if it is the api container:  docker compose stop api" -ForegroundColor Yellow
        }
        Write-Host "    or re-run with -Port 7801" -ForegroundColor Yellow
        throw "Port $Port is already listening."
    }
}
Write-Host "    free"

# --- 3 - the containers -------------------------------------------------------
# The override leaves the `api` service out (a profile nobody enables) and points
# the console at host.docker.internal instead of the compose network.
Step 4 "Qdrant and $Frontend"
if ($SkipDocker) {
    Write-Host "    skipped"
} else {
    docker compose -f docker/backend/compose.yml -f docker/backend/compose.host-api.yml up -d
    if ($LASTEXITCODE -ne 0) { throw "Backend containers could not be started." }

    if ($Frontend -eq "frontend-admin") {
        docker compose -f docker/frontend/compose.yml -f docker/frontend/compose.host-api.yml stop
        docker compose -f docker/frontend/compose-admin.yml -f docker/frontend/compose-admin.host-api.yml up -d
    } else {
        docker compose -f docker/frontend/compose-admin.yml -f docker/frontend/compose-admin.host-api.yml stop
        docker compose -f docker/frontend/compose.yml -f docker/frontend/compose.host-api.yml up -d
    }
    if ($LASTEXITCODE -ne 0) { throw "$Frontend container could not be started." }
    Write-Host "    $Frontend  http://localhost:7800" -ForegroundColor Green
    Write-Host "    qdrant   http://localhost:7833/dashboard" -ForegroundColor Green
}

# --- 4 - corpus ---------------------------------------------------------------
Step 5 "Corpus ingest"
& $venvPython (Join-Path $projectRoot "scripts\ingest_corpus.py") --direct
if ($LASTEXITCODE -ne 0) { throw "Corpus ingestion failed." }

# --- 5 - the API --------------------------------------------------------------
Step 6 "API on this machine"
Write-Host "    swagger  http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "    stop with Ctrl+C - the containers keep running"
Write-Host ""

$uvicornArgs = @("backend.main:app", "--port", "$Port")
if (-not $NoReload) { $uvicornArgs += "--reload" }
# host.docker.internal reaches the host's loopback on Docker Desktop, so 127.0.0.1
# is enough on Windows and macOS. On Docker Engine for Linux the name resolves to
# the bridge gateway - a real interface - so the server has to listen on it too.
if ($BindAll) { $uvicornArgs += @("--host", "0.0.0.0") }

if (Test-Path ".venv\Scripts\uvicorn.exe") {
    & ".venv\Scripts\uvicorn.exe" @uvicornArgs
} else {
    & $venvPython -m uvicorn @uvicornArgs
}
