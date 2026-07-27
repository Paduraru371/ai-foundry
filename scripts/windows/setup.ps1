$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Credentials = Join-Path $ProjectRoot ".credentials"

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
    $PythonPrefix = @("-3")
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
    $PythonPrefix = @()
}
else {
    throw "Python was not found. Install Python 3.11 or newer."
}

$PythonVersion = & $PythonExe @PythonPrefix -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$VersionOk = & $PythonExe @PythonPrefix -c "import sys; print(int(sys.version_info >= (3, 11)))"
if ($VersionOk.Trim() -ne "1") {
    Write-Warning "Python $PythonVersion detected; Python 3.11+ is recommended."
}

if ((Test-Path $VenvDir) -and -not (Test-Path $VenvPython)) {
    throw ".venv was created by another operating system. Remove .venv and run this Windows setup script again."
}
elseif (-not (Test-Path $VenvDir)) {
    Write-Host "Creating shared virtual environment..."
    & $PythonExe @PythonPrefix -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the virtual environment."
    }
}
else {
    Write-Host "Using existing virtual environment: $VenvDir"
}

Write-Host "Installing project dependencies..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not upgrade pip."
}
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Could not install project dependencies."
}

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
if (-not (Test-Path $Credentials)) {
    $CredentialLines = @(
        "SECRET_AZURE_AI_ENDPOINT=",
        "SECRET_AZURE_AI_AUTH=key",
        "SECRET_AZURE_AI_API_KEY=",
        "SECRET_AZURE_AI_CHAT_DEPLOYMENT=gpt-5.1",
        "SECRET_AZURE_AI_EMBEDDING_DEPLOYMENT=text-embedding-3-small"
    )
    [System.IO.File]::WriteAllLines($Credentials, $CredentialLines, $Utf8NoBom)
    Write-Host "Created .credentials for Azure credentials."
}
else {
    Write-Host "Keeping existing Azure credentials: $Credentials"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next:"
Write-Host "  1. Add your Azure credentials to .credentials."
Write-Host "  2. Run .\scripts\windows\start-all.ps1"
