# =============================================================================
# uninstall.ps1
# AoEM Translator - remove the AoEMTranslator Windows service.
#
# Run in an ELEVATED (Administrator) PowerShell window:
#   powershell -ExecutionPolicy Bypass -File .\deploy\windows\uninstall.ps1
#
# Keeps .env (secrets), data\ (settings/stats) and logs\ on disk.
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

function Assert-ExitCode {
    # Fail fast when the previous external (native) command returned an error.
    param(
        [Parameter(Mandatory = $true)][int]$ExitCode,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string]$FailureMessage
    )
    if ($ExitCode -ne 0) {
        Write-Host ''
        Write-Host ('ERROR: "{0}" failed with exit code {1}.' -f $Command, $ExitCode) -ForegroundColor Red
        Write-Host $FailureMessage -ForegroundColor Red
        exit 1
    }
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

# -----------------------------------------------------------------------------
# Locations (project root = two levels up from this script)
# -----------------------------------------------------------------------------
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path

Set-Location -LiteralPath $ProjectRoot
Write-Host ('AoEM Translator - uninstall. Project root: {0}' -f $ProjectRoot)

# Removing a service needs administrator rights.
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Fail 'This script must run in an ELEVATED PowerShell window. Close it, right-click PowerShell, choose "Run as administrator", and run this script again.'
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host ('The service "{0}" is not installed - nothing to uninstall.' -f $ServiceName)
    exit 0
}

$NssmExe = Find-Nssm
if (-not $NssmExe) {
    Write-Fail 'NSSM (nssm.exe) was not found on this machine. Remove the service manually with "nssm stop AoEMTranslator" and then "nssm remove AoEMTranslator confirm", or run deploy\windows\install.ps1 first.'
}

Write-Host 'Stopping the service...'
& $NssmExe stop $ServiceName
$stopExit = $LASTEXITCODE
$svcAfterStop = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (($stopExit -ne 0) -and ($svcAfterStop -and ($svcAfterStop.Status -ne 'Stopped'))) {
    Write-Fail ('Could not stop the service (nssm exit code {0}, service status {1}). Stop it manually with "nssm stop AoEMTranslator" or via services.msc, then run this script again.' -f $stopExit, $svcAfterStop.Status)
}
Start-Sleep -Seconds 2

Write-Host 'Removing the service...'
& $NssmExe remove $ServiceName confirm
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm remove AoEMTranslator confirm' -FailureMessage 'The service could not be removed. Try again manually: nssm remove AoEMTranslator confirm'

Write-Host ('Service "{0}" removed.' -f $ServiceName) -ForegroundColor Green
Write-Host 'Kept on disk: .env (secrets), data\ (settings and stats), logs\. Delete them manually for a full cleanup.'
