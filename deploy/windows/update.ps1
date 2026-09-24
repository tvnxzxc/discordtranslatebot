# =============================================================================
# update.ps1
# AoEM Translator - pull new code, refresh dependencies, restart the service.
#
# Run in an ELEVATED (Administrator) PowerShell window on the home laptop:
#   powershell -ExecutionPolicy Bypass -File .\deploy\windows\update.ps1
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
function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ''
    Write-Host ('=== {0} ===' -f $Message) -ForegroundColor Cyan
}

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
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$RequirementsFile = Join-Path $ProjectRoot 'requirements.txt'
$LogFile = Join-Path $ProjectRoot 'logs\bot.log'

Set-Location -LiteralPath $ProjectRoot
Write-Host ('AoEM Translator - update. Project root: {0}' -f $ProjectRoot)

# Restarting a service needs administrator rights.
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Fail 'This script must run in an ELEVATED PowerShell window. Close it, right-click PowerShell, choose "Run as administrator", and run this script again.'
}

# -----------------------------------------------------------------------------
# Step 1 - Pull the latest code
# -----------------------------------------------------------------------------
Write-Step 'Step 1/4: Pulling the latest code (git pull --ff-only)'
& git.exe pull --ff-only
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'git pull --ff-only' -FailureMessage 'The pull failed. If files were changed locally on the laptop, discard or move those changes aside (check "git status"), then run this script again.'

# -----------------------------------------------------------------------------
# Step 2 - Refresh Python dependencies
# -----------------------------------------------------------------------------
Write-Step 'Step 2/4: Installing Python dependencies'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Fail ('The virtual environment was not found ({0}). Run deploy\windows\install.ps1 first.' -f $VenvPython)
}
if (-not (Test-Path -LiteralPath $RequirementsFile)) {
    Write-Fail 'requirements.txt was not found in the project root. Update the repository and run this script again.'
}
& $VenvPython -m pip install -r $RequirementsFile
Assert-ExitCode -ExitCode $LASTEXITCODE -Command '.venv\Scripts\python.exe -m pip install -r requirements.txt' -FailureMessage 'Installing the dependencies failed. Check your internet connection and the error output above, then run this script again.'

# -----------------------------------------------------------------------------
# Step 3 - Restart the service
# -----------------------------------------------------------------------------
Write-Step 'Step 3/4: Restarting the AoEMTranslator service'
$NssmExe = Find-Nssm
if (-not $NssmExe) {
    Write-Fail 'NSSM (nssm.exe) was not found on this machine. Run deploy\windows\install.ps1 first.'
}
& $NssmExe restart $ServiceName
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm restart AoEMTranslator' -FailureMessage 'The service could not be restarted. Is it installed? Run deploy\windows\install.ps1 if the service is missing, then run this script again.'
Start-Sleep -Seconds 3

# -----------------------------------------------------------------------------
# Step 4 - Show status and the last log lines
# -----------------------------------------------------------------------------
Write-Step 'Step 4/4: Service status and recent log lines'
$statusOutput = Get-ServiceStatusText -NssmPath $NssmExe -Name $ServiceName
Write-Host ('Service status: {0}' -f $statusOutput)

if (Test-Path -LiteralPath $LogFile) {
    Write-Host '--- Last 15 lines of logs\bot.log ---'
    Get-Content -LiteralPath $LogFile -Tail 15
    Write-Host '--------------------------------------'
}
else {
    Write-Host 'logs\bot.log does not exist yet. Wait a few seconds and run this script again.'
}

if ($statusOutput -notmatch 'SERVICE_RUNNING') {
    Write-Host ''
    Write-Host 'WARNING: the service is not RUNNING after the update. Read logs\bot.log above for the reason.' -ForegroundColor Yellow
    exit 1
}
Write-Host 'Update finished - the service is running.' -ForegroundColor Green
