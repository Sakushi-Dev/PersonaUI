@echo off
setlocal enabledelayedexpansion
title PersonaUI - Python Installation
color 0B

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║    Python 3.12 - Automatische Installation   ║
echo   ╚══════════════════════════════════════════════╝
echo.

REM ──────────────────────────────────────────────
REM  Prüfe ob Python bereits vorhanden
REM ──────────────────────────────────────────────

where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
    echo   [OK] !PY_VER! ist bereits installiert.
    echo.
    exit /b 0
)

where py >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('py --version 2^>^&1') do set "PY_VER=%%i"
    echo   [OK] !PY_VER! ist bereits installiert.
    echo.
    exit /b 0
)

REM ──────────────────────────────────────────────
REM  Python herunterladen
REM ──────────────────────────────────────────────

echo   Python wird heruntergeladen...
echo   (Python 3.12.8 - ca. 25 MB)
echo.

set "PY_INSTALLER=%TEMP%\python-3.12.8-installer.exe"

powershell -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"

if not exist "%PY_INSTALLER%" (
    echo   [FEHLER] Download fehlgeschlagen!
    echo   Bitte pruefe deine Internetverbindung.
    echo   Manueller Download: https://www.python.org/downloads/
    echo.
    exit /b 1
)

echo   [OK] Download abgeschlossen.
echo.

REM ──────────────────────────────────────────────
REM  Python installieren (leise, mit PATH)
REM ──────────────────────────────────────────────

echo   Python wird installiert...
echo   (Add to PATH wird automatisch aktiviert)
echo.

"%PY_INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0

if %errorlevel% neq 0 (
    echo   [FEHLER] Python Installation fehlgeschlagen!
    echo   Bitte installiere Python manuell: https://www.python.org/downloads/
    del "%PY_INSTALLER%" >nul 2>&1
    echo.
    exit /b 1
)

REM Installer aufräumen
del "%PY_INSTALLER%" >nul 2>&1

REM PATH für aktuelle Session aktualisieren
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"

REM ──────────────────────────────────────────────
REM  Verifizieren
REM ──────────────────────────────────────────────

where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
    echo   [OK] !PY_VER! erfolgreich installiert!
    echo.
    exit /b 0
)

REM Direkt prüfen falls where noch nicht aktualisiert
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo   [OK] Python 3.12 erfolgreich installiert!
    echo   (PATH wird nach Neustart der Konsole aktiv)
    echo.
    exit /b 0
)

echo   [WARNUNG] Python wurde installiert, konnte aber nicht verifiziert werden.
echo   Bitte starte eine NEUE Eingabeaufforderung und versuche es erneut.
echo.
exit /b 1
