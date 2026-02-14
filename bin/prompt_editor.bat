@echo off
:: ============================================================
:: Startet den PersonaUI Prompt Editor
:: Eigenständiges PyWebView-Fenster zum Bearbeiten von Prompts
:: ============================================================
setlocal enabledelayedexpansion
title PersonaUI Prompt Editor

REM ══════════════════════════════════════════════════════════════════════
REM  Pfade bestimmen - funktioniert als .bat (bin/) UND als .exe (Root)
REM ══════════════════════════════════════════════════════════════════════

set "SELF_DIR=%~dp0"

REM Prüfe ob wir im Root liegen (.exe) oder in bin/ (.bat)
if exist "%SELF_DIR%src\app.py" (
    set "ROOT=%SELF_DIR%"
) else if exist "%SELF_DIR%..\src\app.py" (
    set "ROOT=%SELF_DIR%.."
) else (
    echo [FEHLER] src\app.py nicht gefunden!
    echo Bitte starte die Anwendung aus dem PersonaUI Ordner.
    pause
    exit /b 1
)

REM Trailing Backslash normalisieren
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"

REM ══════════════════════════════════════════════════════════════════════
REM  Python prüfen
REM ══════════════════════════════════════════════════════════════════════

set "PYTHON_CMD="

REM 1. venv Python bevorzugen
if exist "%VENV_PY%" (
    set "PYTHON_CMD=%VENV_PY%"
    goto :python_ok
)

REM 2. System Python prüfen
where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto :python_ok
)

REM 3. py Launcher prüfen
where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
    goto :python_ok
)

echo [FEHLER] Python wurde nicht gefunden!
echo Bitte zuerst install_py12.bat ausfuehren.
pause
exit /b 1

:python_ok

REM ══════════════════════════════════════════════════════════════════════
REM  Prompt Editor starten
REM ══════════════════════════════════════════════════════════════════════

cd /d "%ROOT%\src"
"%PYTHON_CMD%" -m prompt_editor.editor

if errorlevel 1 (
    echo.
    echo Ein Fehler ist aufgetreten!
    pause
)
