@echo off
echo Starte PersonaUI Reset...
echo.

REM ══════════════════════════════════════════════════════════════════════
REM  Pfade bestimmen - funktioniert als .bat (bin/) UND als .exe (Root)
REM ══════════════════════════════════════════════════════════════════════

set "SELF_DIR=%~dp0"

REM Prüfe ob wir im Root liegen (.exe) oder in bin/ (.bat)
if exist "%SELF_DIR%src\reset.py" (
    set "ROOT=%SELF_DIR%"
) else if exist "%SELF_DIR%..\src\reset.py" (
    set "ROOT=%SELF_DIR%.."
) else (
    echo [FEHLER] src\reset.py nicht gefunden!
    echo Bitte starte die Anwendung aus dem PersonaUI Ordner.
    pause
    exit /b 1
)

REM Trailing Backslash normalisieren
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"

REM Python prüfen
if not exist "%VENV_PY%" (
    echo [FEHLER] .venv nicht gefunden! Bitte zuerst start.bat ausfuehren.
    pause
    exit /b 1
)

REM Wechsel ins src Verzeichnis
cd /d "%ROOT%\src"

REM Starte die Reset-Anwendung im PyWebView-Fenster
"%VENV_PY%" reset.py

REM Schließe das Fenster automatisch
if errorlevel 1 (
    echo.
    echo Ein Fehler ist aufgetreten!
    pause
) else (
    exit
)
