# =============================================================================
# install.ps1
# AoEM Translator - one-time installation on the home Windows laptop.
#
# Run ONCE in an ELEVATED (Administrator) PowerShell window:
#   1. Right-click PowerShell -> "Run as administrator"
#   2. cd C:\path\to\discordtranslatebot
#   3. powershell -ExecutionPolicy Bypass -File .\deploy\windows\install.ps1
#
# Implements SPEC.md section 6, steps 1-8, in order. Every step prints what it
# does and the script stops with a clear message on the first failure.
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

function Get-PlaintextFromSecureString {
    # Converts a SecureString (from Read-Host -AsSecureString) to plain text
    # WITHOUT ever printing it. Only used to write the value into .env.
    param([Parameter(Mandatory = $true)][System.Security.SecureString]$SecureValue)
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Set-EnvValue {
    # Sets KEY=value in a .env file: replaces the line if the key exists,
    # appends it otherwise. Writes UTF-8 WITHOUT BOM (python-dotenv safe).
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value
    )
    [string[]]$lines = [System.IO.File]::ReadAllLines($Path)
    $pattern = '^\s*' + [System.Text.RegularExpressions.Regex]::Escape($Key) + '\s*='
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = ('{0}={1}' -f $Key, $Value)
            $found = $true
        }
    }
    if (-not $found) {
        $lines += ('{0}={1}' -f $Key, $Value)
    }
    [System.IO.File]::WriteAllLines($Path, $lines)
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
$EnvFile = Join-Path $ProjectRoot '.env'
$EnvExampleFile = Join-Path $ProjectRoot '.env.example'
$VenvDir = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$LogsDir = Join-Path $ProjectRoot 'logs'
$LogFile = Join-Path $LogsDir 'bot.log'
$RequirementsFile = Join-Path $ProjectRoot 'requirements.txt'
$BotFile = Join-Path $ProjectRoot 'bot.py'

# Refuse to install inside the Windows directory: C:\WINDOWS\... has
# restrictive ACLs that break .env access, and Windows may clean it up.
if ($ProjectRoot -like (Join-Path $env:windir '*')) {
    Write-Fail (
        'This repo is inside the Windows directory (' + $ProjectRoot + ').' +
        " It must not live there - system32-style ACLs break .env access and Windows may clean it up.`n" +
        'Delete this folder, then clone somewhere normal and run this script again, e.g.:' +
        "`n    git clone https://github.com/tvnxzxc/discordtranslatebot C:\discordtranslatebot" +
        "`n    cd C:\discordtranslatebot" +
        "`n    powershell -ExecutionPolicy Bypass -File .\deploy\windows\install.ps1"
    )
}

Set-Location -LiteralPath $ProjectRoot

Write-Host 'AoEM Translator - one-time install for the home laptop (Windows service via NSSM).'
Write-Host ('Project root: {0}' -f $ProjectRoot)

# -----------------------------------------------------------------------------
# Elevation check (a Windows service can only be installed as administrator)
# -----------------------------------------------------------------------------
Write-Step 'Step 0/8: Checking for an elevated (Administrator) PowerShell'
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Fail 'This script must run in an ELEVATED PowerShell window. Close it, right-click PowerShell, choose "Run as administrator", and run this script again.'
}
Write-Host 'Running as administrator: OK.'

# -----------------------------------------------------------------------------
# Step 1 - Prerequisites: git, Python 3.11+, winget
# -----------------------------------------------------------------------------
Write-Step 'Step 1/8: Checking prerequisites (git, Python 3.11+, winget)'

if (-not (Get-Command -Name 'git.exe' -ErrorAction SilentlyContinue)) {
    Write-Fail 'git was not found. Install Git for Windows from https://git-scm.com/download/win (default options are fine), then run this script again.'
}
& git.exe --version
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'git --version' -FailureMessage 'git is installed but broken. Reinstall Git for Windows from https://git-scm.com/download/win and run this script again.'

# Python: prefer the py launcher ("py -3"), fall back to "python".
$PyExe = $null
$PyArgs = @()
if (Get-Command -Name 'py.exe' -ErrorAction SilentlyContinue) {
    & py.exe -3 --version
    if ($LASTEXITCODE -eq 0) {
        $PyExe = (Get-Command -Name 'py.exe' -ErrorAction SilentlyContinue).Path
        $PyArgs = @('-3')
    }
}
if (-not $PyExe) {
    if (Get-Command -Name 'python.exe' -ErrorAction SilentlyContinue) {
        & python.exe --version
        if ($LASTEXITCODE -eq 0) {
            $PyExe = (Get-Command -Name 'python.exe' -ErrorAction SilentlyContinue).Path
            $PyArgs = @()
        }
    }
}
if (-not $PyExe) {
    Write-Fail 'Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/ and CHECK the box "Add python.exe to PATH" in the installer, then run this script again.'
}

# Verify the interpreter is at least Python 3.11 (best effort on the output).
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $pyVersionText = ((& $PyExe @PyArgs --version 2>&1) | Out-String).Trim()
}
catch {
    $pyVersionText = ''
}
finally {
    $ErrorActionPreference = $oldEap
}
if ($pyVersionText -match 'Python\s+(\d+)\.(\d+)') {
    $pyMajor = [int]$Matches[1]
    $pyMinor = [int]$Matches[2]
    if (($pyMajor -lt 3) -or (($pyMajor -eq 3) -and ($pyMinor -lt 11))) {
        Write-Fail ('Python {0}.{1} was found, but Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ (CHECK "Add python.exe to PATH"), then run this script again.' -f $pyMajor, $pyMinor)
    }
    Write-Host ('Python: OK ({0}).' -f $pyVersionText)
}
else {
    Write-Host ('Python found, but the version could not be read (output: {0}). Continuing anyway.' -f $pyVersionText) -ForegroundColor Yellow
}

if (-not (Get-Command -Name 'winget.exe' -ErrorAction SilentlyContinue)) {
    Write-Fail 'winget (Windows Package Manager) was not found. Install "App Installer" from the Microsoft Store (or from https://aka.ms/getwinget), then run this script again. winget is needed to install NSSM.'
}
& winget.exe --version
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'winget --version' -FailureMessage 'winget is present but not working. Update "App Installer" from the Microsoft Store and run this script again.'
Write-Host 'Prerequisites: OK.'

# -----------------------------------------------------------------------------
# Step 2 - .env: create from .env.example, ask for secrets, lock down ACL
# -----------------------------------------------------------------------------
Write-Step 'Step 2/8: Preparing the .env file (secrets)'

if (Test-Path -LiteralPath $EnvFile) {
    Write-Host '.env already exists - keeping the existing values (they are NOT shown).'
    Write-Host 'If any value in .env is empty, edit .env in Notepad, or delete it and run this script again.'
}
else {
    if (-not (Test-Path -LiteralPath $EnvExampleFile)) {
        Write-Fail '.env.example was not found in the project root. Update the repository (git pull / git clone) and run this script again.'
    }
    Copy-Item -LiteralPath $EnvExampleFile -Destination $EnvFile
    Write-Host 'Created .env from .env.example.'

    Write-Host 'Enter the values below (copy them from the .env file on the dev machine).'
    Write-Host 'Secret input is hidden while you type, and the values are never printed back.'

    do {
        $secureToken = Read-Host -Prompt 'DISCORD_TOKEN' -AsSecureString
        $discordToken = Get-PlaintextFromSecureString -SecureValue $secureToken
        if ([string]::IsNullOrWhiteSpace($discordToken)) {
            Write-Host 'DISCORD_TOKEN must not be empty - try again.' -ForegroundColor Yellow
        }
    } while ([string]::IsNullOrWhiteSpace($discordToken))

    do {
        $secureKey = Read-Host -Prompt 'DEEPL_API_KEY' -AsSecureString
        $deeplApiKey = Get-PlaintextFromSecureString -SecureValue $secureKey
        if ([string]::IsNullOrWhiteSpace($deeplApiKey)) {
            Write-Host 'DEEPL_API_KEY must not be empty - try again.' -ForegroundColor Yellow
        }
    } while ([string]::IsNullOrWhiteSpace($deeplApiKey))

    do {
        $devGuildId = (Read-Host -Prompt 'DEV_GUILD_ID (your Discord server ID; press Enter to leave empty)').Trim()
        if (($devGuildId -ne '') -and ($devGuildId -notmatch '^[0-9]+$')) {
            Write-Host 'DEV_GUILD_ID must be a numeric server ID (or empty for global slash-command sync) - try again.' -ForegroundColor Yellow
        }
    } while (($devGuildId -ne '') -and ($devGuildId -notmatch '^[0-9]+$'))

    Set-EnvValue -Path $EnvFile -Key 'DISCORD_TOKEN' -Value $discordToken
    Set-EnvValue -Path $EnvFile -Key 'DEEPL_API_KEY' -Value $deeplApiKey
    Set-EnvValue -Path $EnvFile -Key 'DEV_GUILD_ID' -Value $devGuildId

    # Drop the plaintext values from memory as soon as possible.
    $discordToken = $null
    $deeplApiKey = $null
    $secureToken = $null
    $secureKey = $null
    Write-Host 'Values written to .env.'
}

Write-Host 'Restricting .env permissions (current user + SYSTEM only)...'
# Use the full Windows identity (MACHINE\user) from the OS itself - on some
# machines $env:USERNAME resolves to a trustee icacls cannot map, which
# silently strips ALL human access from .env.
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $EnvFile /inheritance:r /grant:r "$($identity):F" /grant:r 'SYSTEM:F'
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'icacls .env /inheritance:r /grant:r ...' -FailureMessage 'Could not restrict permissions on .env. Make sure you run this script as administrator and that no program has the .env file open, then run this script again.'
# Prove .env is still readable by this very user - a broken ACE here would
# make the bot itself fail with PermissionError on startup.
try {
    [void](Get-Content -LiteralPath $EnvFile -TotalCount 1)
}
catch {
    Write-Fail ('.env is NOT readable after restricting permissions (' + $_.Exception.Message + '). ' +
        'Recover with: icacls .env /reset   - then report this error.')
}
Write-Host '.env permissions restricted: OK.'

# -----------------------------------------------------------------------------
# Step 3 - venv: create if missing, upgrade pip, install requirements
# -----------------------------------------------------------------------------
Write-Step 'Step 3/8: Creating the virtual environment and installing dependencies'

if (-not (Test-Path -LiteralPath $RequirementsFile)) {
    Write-Fail 'requirements.txt was not found in the project root. Update the repository (git pull / git clone) and run this script again.'
}

if (Test-Path -LiteralPath $VenvPython) {
    Write-Host '.venv already exists - reusing it.'
}
else {
    Write-Host 'Creating .venv (this can take a moment)...'
    & $PyExe @PyArgs -m venv $VenvDir
    Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'python -m venv .venv' -FailureMessage 'Could not create the virtual environment. Delete the .venv folder (if it was partly created) and run this script again.'
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Fail 'venv creation did not produce .venv\Scripts\python.exe. Delete the .venv folder and run this script again.'
    }
}

Write-Host 'Upgrading pip...'
& $VenvPython -m pip install -U pip
Assert-ExitCode -ExitCode $LASTEXITCODE -Command '.venv\Scripts\python.exe -m pip install -U pip' -FailureMessage 'The pip upgrade failed. Check your internet connection and the output above, then run this script again.'

Write-Host 'Installing requirements.txt...'
& $VenvPython -m pip install -r $RequirementsFile
Assert-ExitCode -ExitCode $LASTEXITCODE -Command '.venv\Scripts\python.exe -m pip install -r requirements.txt' -FailureMessage 'Installing the dependencies failed. Check your internet connection and the error output above, then run this script again.'
Write-Host 'Dependencies: OK.'

# -----------------------------------------------------------------------------
# Step 4 - Self-test (must not connect to Discord; exits nonzero on error)
# -----------------------------------------------------------------------------
Write-Step 'Step 4/8: Running the bot self-test (bot.py --selftest)'

if (-not (Test-Path -LiteralPath $BotFile)) {
    Write-Fail 'bot.py was not found in the project root. Update the repository (git pull / git clone) and run this script again.'
}
& $VenvPython $BotFile --selftest
Assert-ExitCode -ExitCode $LASTEXITCODE -Command '.venv\Scripts\python.exe bot.py --selftest' -FailureMessage 'The bot self-test FAILED. Read the error output above (usually a bad .env value or a broken dependency install), fix it, and run this script again.'
Write-Host 'Self-test passed.'

# -----------------------------------------------------------------------------
# Step 5 - NSSM: install via winget if missing, then locate nssm.exe
# -----------------------------------------------------------------------------
Write-Step 'Step 5/8: Installing NSSM (Non-Sucking Service Manager)'

$NssmExe = Find-Nssm
if (-not $NssmExe) {
    Write-Host 'nssm.exe not found - installing via winget...'
    & winget.exe install --id NSSM.NSSM -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host ('winget exited with code {0} (the package may already be installed, or the source was unreachable). Trying to locate nssm.exe anyway...' -f $LASTEXITCODE) -ForegroundColor Yellow
    }
    $NssmExe = Find-Nssm
}
if (-not $NssmExe) {
    Write-Fail 'nssm.exe could not be found after the winget install. Close this window, open a NEW administrator PowerShell window (so PATH refreshes), and run this script again. If it still fails, download NSSM from https://nssm.cc and place nssm.exe in a folder that is on PATH.'
}
Write-Host ('NSSM found: {0}' -f $NssmExe)

# -----------------------------------------------------------------------------
# Step 6 - Service: remove any old install, then register, configure, start
# -----------------------------------------------------------------------------
Write-Step 'Step 6/8: Installing the AoEMTranslator Windows service'

$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host 'The service already exists - stopping and removing the old one first...'
    & $NssmExe stop $ServiceName
    $stopExit = $LASTEXITCODE
    $svcAfterStop = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (($stopExit -ne 0) -and ($svcAfterStop -and ($svcAfterStop.Status -ne 'Stopped'))) {
        Write-Fail ('Could not stop the existing service (nssm exit code {0}, service status {1}). Stop it manually with "nssm stop AoEMTranslator" or via services.msc, then run this script again.' -f $stopExit, $svcAfterStop.Status)
    }
    Start-Sleep -Seconds 2
    & $NssmExe remove $ServiceName confirm
    Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm remove AoEMTranslator confirm' -FailureMessage 'Could not remove the existing service. Remove it manually with "nssm remove AoEMTranslator confirm", then run this script again.'
}

if (-not (Test-Path -LiteralPath $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}
Write-Host ('Logs directory: {0}' -f $LogsDir)

Write-Host 'Registering the service...'
& $NssmExe install $ServiceName $VenvPython 'bot.py'
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm install AoEMTranslator' -FailureMessage 'Service registration failed. Run this script again; if it keeps failing, remove any half-created service with "nssm remove AoEMTranslator confirm".'

Write-Host 'Configuring the service...'
& $NssmExe set $ServiceName AppDirectory $ProjectRoot
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppDirectory' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName DisplayName 'AoEM Translator Discord Bot'
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set DisplayName' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName Description 'Discord translation bot (flag reactions, DeepL)'
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set Description' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName Start SERVICE_AUTO_START
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set Start SERVICE_AUTO_START' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppExit Default Restart
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppExit Default Restart' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppRestartDelay 5000
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppRestartDelay 5000' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppStdout $LogFile
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppStdout' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppStderr $LogFile
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppStderr' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppRotateFiles 1
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppRotateFiles 1' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppRotateOnline 1
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppRotateOnline 1' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppRotateBytes 5242880
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppRotateBytes 5242880' -FailureMessage 'Configuring the service failed. Run this script again.'
& $NssmExe set $ServiceName AppEnvironmentExtra 'PYTHONUNBUFFERED=1' 'PYTHONIOENCODING=utf-8'
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm set AppEnvironmentExtra' -FailureMessage 'Configuring the service failed. Run this script again.'
Write-Host 'Service configured.'

Write-Host 'Starting the service...'
& $NssmExe start $ServiceName
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'nssm start AoEMTranslator' -FailureMessage 'The service could not be started. Check logs\bot.log for errors, then run this script again.'
Write-Host 'Waiting a few seconds for the bot to connect...'
Start-Sleep -Seconds 5

# -----------------------------------------------------------------------------
# Step 7 - Power settings: laptop must not sleep, lid close must not stop it
# -----------------------------------------------------------------------------
Write-Step 'Step 7/8: Applying power settings (laptop must stay on 24/7)'

& powercfg.exe /change standby-timeout-ac 0
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'powercfg /change standby-timeout-ac 0' -FailureMessage 'Applying the power settings failed. Run this script again.'
& powercfg.exe /change hibernate-timeout-ac 0
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'powercfg /change hibernate-timeout-ac 0' -FailureMessage 'Applying the power settings failed. Run this script again.'
& powercfg.exe /change monitor-timeout-ac 10
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'powercfg /change monitor-timeout-ac 10' -FailureMessage 'Applying the power settings failed. Run this script again.'
& powercfg.exe /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0' -FailureMessage 'Applying the power settings failed. Run this script again.'
& powercfg.exe /setactive SCHEME_CURRENT
Assert-ExitCode -ExitCode $LASTEXITCODE -Command 'powercfg /setactive SCHEME_CURRENT' -FailureMessage 'Applying the power settings failed. Run this script again.'

Write-Host 'Power settings applied. Also remember to:'
Write-Host '  - Keep the laptop plugged in (it must not run on battery 24/7).'
Write-Host '  - Prefer a wired Ethernet connection if possible.'
Write-Host '  - If you use Wi-Fi: in Device Manager open the wireless adapter properties and DISABLE "Allow the computer to turn off this device to save power".'
Write-Host '  - Set Windows Update "active hours" so automatic reboots do not interrupt the bot.'

# -----------------------------------------------------------------------------
# Step 8 - Result: service status + last log lines
# -----------------------------------------------------------------------------
Write-Step 'Step 8/8: Verifying the service'

$statusOutput = Get-ServiceStatusText -NssmPath $NssmExe -Name $ServiceName
Write-Host ('Service status: {0}' -f $statusOutput)

if (Test-Path -LiteralPath $LogFile) {
    Write-Host '--- Last 20 lines of logs\bot.log ---'
    Get-Content -LiteralPath $LogFile -Tail 20
    Write-Host '--------------------------------------'
}
else {
    Write-Host 'logs\bot.log does not exist yet. Wait a few seconds, then run deploy\windows\status.ps1.'
}

if ($statusOutput -notmatch 'SERVICE_RUNNING') {
    Write-Host ''
    Write-Host 'The service is not RUNNING yet. Wait a few seconds and run deploy\windows\status.ps1.'
    Write-Host 'If it stays down, read logs\bot.log for the error, fix it, and run install.ps1 again.'
    exit 1
}

Write-Host ''
Write-Host 'Install finished - the bot is running as a Windows service.' -ForegroundColor Green
Write-Host 'The bot invite link is printed in logs\bot.log (look for discord.com/oauth2/authorize).'
Write-Host 'IMPORTANT: stop any OTHER running copy of the bot (for example the local bot on your dev machine).'
Write-Host 'Two copies running at once add double flags and post double translations.'
