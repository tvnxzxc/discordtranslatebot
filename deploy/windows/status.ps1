# =============================================================================
# status.ps1
# AoEM Translator - show the service status and the last 30 log lines.
#
# Works from ANY PowerShell window (no administrator rights needed):
#   powershell -ExecutionPolicy Bypass -File .\deploy\windows\status.ps1
#
# All text in this file is English/ASCII on purpose (avoids codepage bugs).
# =============================================================================

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ServiceName = 'AoEMTranslator'

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
function Write-Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ''
    Write-Host ('ERROR: {0}' -f $Message) -ForegroundColor Red
    exit 1
}

function Find-Nssm {
    # Returns the full path to nssm.exe, or $null if it cannot be found.
    # Checks PATH first, then the winget portable-package folder.
    $cmd = Get-Command -Name 'nssm.exe' -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Path
    }
    $searchRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (Test-Path -LiteralPath $searchRoot) {
        $hit = Get-ChildItem -LiteralPath $searchRoot -Filter 'nssm.exe' -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) {
            return $hit.FullName
        }
    }
    return $null
}

function Get-ServiceStatusText {
    # Runs "nssm status <name>" and returns its output as one trimmed string.
    param(
        [Parameter(Mandatory = $true)][string]$NssmPath,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        return ((& $NssmPath status $Name 2>&1) | Out-String).Trim()
    }
    catch {
        return 'UNKNOWN'
    }
    finally {
        $ErrorActionPreference = $oldEap
    }
}

# -----------------------------------------------------------------------------
# Locations (project root = two levels up from this script)
# -----------------------------------------------------------------------------
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$LogFile = Join-Path $ProjectRoot 'logs\bot.log'

Set-Location -LiteralPath $ProjectRoot
Write-Host ('AoEM Translator - status. Project root: {0}' -f $ProjectRoot)

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Fail ('The Windows service "{0}" is not installed on this machine. Run deploy\windows\install.ps1 to install it.' -f $ServiceName)
}

$NssmExe = Find-Nssm
if (-not $NssmExe) {
    Write-Host ('Windows reports the service state as: {0}' -f $svc.Status)
    Write-Fail 'NSSM (nssm.exe) was not found on this machine, so the detailed NSSM status cannot be read. Run deploy\windows\install.ps1 first.'
}

$statusOutput = Get-ServiceStatusText -NssmPath $NssmExe -Name $ServiceName
Write-Host ('Service status: {0}' -f $statusOutput)
if ($statusOutput -match 'SERVICE_RUNNING') {
    Write-Host 'The service is running.' -ForegroundColor Green
}
else {
    Write-Host 'The service is NOT running.' -ForegroundColor Yellow
}

if (Test-Path -LiteralPath $LogFile) {
    Write-Host '--- Last 30 lines of logs\bot.log ---'
    Get-Content -LiteralPath $LogFile -Tail 30 -Encoding UTF8
    Write-Host '--------------------------------------'
}
else {
    Write-Host 'logs\bot.log does not exist yet (the bot has not written a log).'
}
