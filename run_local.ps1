# =============================================================================
# run_local.ps1
# AoEM Translator - run the bot locally on the DEV machine.
#
# - creates .venv if it does not exist yet (py -3 -m venv .venv)
# - installs requirements.txt + requirements-dev.txt
# - runs the bot directly via .venv\Scripts\python.exe bot.py
#
# NOTE: this script never "activates" the venv (no Activate.ps1 / Activate.bat
# - execution policy issues). Calling .venv\Scripts\python.exe directly avoids
# that entirely.
#
# Extra arguments are passed through to bot.py, for example:
#   powershell -ExecutionPolicy Bypass -File .\run_local.ps1 --selftest
#
# All text in this file is English/ASCII on purpose (avoids codepage bugs).
# =============================================================================

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$VenvDir = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$BotFile = Join-Path $ProjectRoot 'bot.py'
$RequirementsFile = Join-Path $ProjectRoot 'requirements.txt'
$RequirementsDevFile = Join-Path $ProjectRoot 'requirements-dev.txt'

Set-Location -LiteralPath $ProjectRoot

Write-Host ('AoEM Translator - local run. Project root: {0}' -f $ProjectRoot)

# -----------------------------------------------------------------------------
# Create .venv if it is missing
# -----------------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host 'Creating the virtual environment (.venv)...'
    if (Get-Command -Name 'py.exe' -ErrorAction SilentlyContinue) {
        & py.exe -3 -m venv $VenvDir
    }
    elseif (Get-Command -Name 'python.exe' -ErrorAction SilentlyContinue) {
        & python.exe -m venv $VenvDir
    }
    else {
        Write-Host ''
        Write-Host 'ERROR: neither py.exe nor python.exe was found on PATH.' -ForegroundColor Red
        Write-Host 'Install Python 3.11+ from https://www.python.org/downloads/ and CHECK "Add python.exe to PATH", then run this script again.' -ForegroundColor Red
        exit 1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host ('ERROR: venv creation failed with exit code {0}. Delete the .venv folder and run this script again.' -f $LASTEXITCODE) -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Host ''
        Write-Host 'ERROR: venv creation did not produce .venv\Scripts\python.exe. Delete the .venv folder and run this script again.' -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host '.venv already exists - reusing it.'
}

# -----------------------------------------------------------------------------
# Install / refresh dependencies (runtime + dev)
# -----------------------------------------------------------------------------
if ((-not (Test-Path -LiteralPath $RequirementsFile)) -or (-not (Test-Path -LiteralPath $RequirementsDevFile))) {
    Write-Host ''
    Write-Host 'ERROR: requirements.txt and/or requirements-dev.txt were not found in the project root. Update the repository (git pull) and run this script again.' -ForegroundColor Red
    exit 1
}

Write-Host 'Installing dependencies (requirements.txt, requirements-dev.txt)...'
& $VenvPython -m pip install -r $RequirementsFile -r $RequirementsDevFile
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host ('ERROR: pip install failed with exit code {0}. Check the output above (internet connection / error message) and run this script again.' -f $LASTEXITCODE) -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------------
# Run the bot (no venv activation - direct python.exe call)
# -----------------------------------------------------------------------------
Write-Host 'Starting the bot (press Ctrl+C to stop)...'
& $VenvPython $BotFile @args
exit $LASTEXITCODE
