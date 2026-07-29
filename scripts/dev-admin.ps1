<#
.SYNOPSIS
  Runs the backend with the server-rendered administration frontend.

.DESCRIPTION
  Uses the same development workflow as dev.ps1, selecting frontend-admin.
#>
param(
    [int]$Port = 7799,
    [switch]$BindAll,
    [switch]$SkipDocker,
    [switch]$NoReload,
    [switch]$Force
)

$arguments = @{} + $PSBoundParameters
$arguments["Frontend"] = "frontend-admin"
& (Join-Path $PSScriptRoot "dev.ps1") @arguments
exit $LASTEXITCODE
