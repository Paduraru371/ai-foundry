<#
.SYNOPSIS
  Runs the backend with the server-rendered administration frontend.

.DESCRIPTION
  Uses the same development workflow as dev.ps1, selecting frontend-admin.
#>
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 7799,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 7800,
    [switch]$BindAll,
    [switch]$SkipDocker,
    [switch]$NoReload,
    [switch]$Force
)

$arguments = @{} + $PSBoundParameters
$arguments["Frontend"] = "frontend-admin"
& (Join-Path $PSScriptRoot "dev.ps1") @arguments
exit $LASTEXITCODE
