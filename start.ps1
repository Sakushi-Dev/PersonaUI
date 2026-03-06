# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Start (PowerShell – Cross-Platform)
# ══════════════════════════════════════════════════════════════════════
$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "PersonaUI"

Write-Host "Initialisiere PersonaUI..."

# ══════════════════════════════════════════════════════════════════════
#  Pfade bestimmen
# ══════════════════════════════════════════════════════════════════════

$SelfDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Test-Path (Join-Path $SelfDir "src/app.py")) {
    $Root = $SelfDir
} elseif (Test-Path (Join-Path $SelfDir "../src/app.py")) {
    $Root = Resolve-Path (Join-Path $SelfDir "..")
} else {
    Write-Host "[FEHLER] src/app.py nicht gefunden!"
    Write-Host "Bitte starte die Anwendung aus dem PersonaUI Ordner."
    Read-Host "Enter drücken zum Beenden"
    exit 1
}

$IsWindows_ = ($PSVersionTable.PSEdition -eq "Desktop") -or ($IsWindows -eq $true)

if ($IsWindows_) {
    $VenvPy = Join-Path $Root ".venv/Scripts/python.exe"
} else {
    $VenvPy = Join-Path $Root ".venv/bin/python"
}
$Init = Join-Path $Root "src/init.py"

# ══════════════════════════════════════════════════════════════════════
#  Python prüfen
# ══════════════════════════════════════════════════════════════════════

$PythonCmd = $null

# 1. venv Python bevorzugen
if (Test-Path $VenvPy) {
    $PythonCmd = $VenvPy
}
# 2. python3 prüfen (Linux/macOS)
elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
}
# 3. python prüfen
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
}
# 4. py Launcher prüfen (Windows)
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host ""
    Write-Host "  Python wurde nicht gefunden!"
    Write-Host "  Python 3.10+ wird fuer PersonaUI benoetigt."
    Write-Host ""
    if ($IsWindows_) {
        Write-Host "  Download: https://www.python.org/downloads/"
    } else {
        Write-Host "  Installiere Python mit deinem Paketmanager:"
        Write-Host "    Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
        Write-Host "    Fedora:        sudo dnf install python3 python3-pip"
        Write-Host "    Arch:          sudo pacman -S python python-pip"
        Write-Host "    macOS:         brew install python"
    }
    Write-Host ""
    Read-Host "Enter drücken zum Beenden"
    exit 1
}

# ══════════════════════════════════════════════════════════════════════
#  Launch Options laden (config/launch_options.txt)
# ══════════════════════════════════════════════════════════════════════

$LaunchOpts = @()
$LaunchFile = Join-Path $Root "config/launch_options.txt"

if (Test-Path $LaunchFile) {
    Get-Content $LaunchFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $LaunchOpts += $line -split '\s+'
        }
    }
}

# ══════════════════════════════════════════════════════════════════════
#  App starten (init.py → installiert bei Bedarf → startet app.py)
# ══════════════════════════════════════════════════════════════════════

$AllArgs = $args + $LaunchOpts
& $PythonCmd $Init @AllArgs
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Host ""
    Write-Host "Ein Fehler ist aufgetreten! (Exit Code: $ExitCode)"
    Read-Host "Enter drücken zum Beenden"
}
