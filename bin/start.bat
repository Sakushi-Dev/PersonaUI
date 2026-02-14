@echo off
echo Initialisiere PersonaUI...
setlocal enabledelayedexpansion
title PersonaUI
color 0B

REM ══════════════════════════════════════════════════════════════════════
REM  Pfade bestimmen - funktioniert als .bat (bin/) UND als .exe (Root)
REM ══════════════════════════════════════════════════════════════════════

set "SELF_DIR=%~dp0"

REM Prüfe ob wir im Root liegen (.exe) oder in bin/ (.bat)
REM Wenn src/ als Unterordner existiert → wir sind im Root
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
set "INIT=%ROOT%\src\init.py"
set "BIN_DIR=%ROOT%\bin"

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

REM 4. Python nicht gefunden → Installer anbieten
echo.
echo   Python wurde nicht gefunden!
echo   Python 3.10+ wird fuer PersonaUI benoetigt.
echo.

if exist "%BIN_DIR%\install_py12.bat" (
    echo   Starte automatische Python-Installation...
    echo.
    call "%BIN_DIR%\install_py12.bat"
    if !errorlevel! neq 0 (
        echo   [FEHLER] Python-Installation fehlgeschlagen.
        pause
        exit /b 1
    )
    REM PATH neu laden
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"
    where python >nul 2>&1
    if !errorlevel!==0 (
        set "PYTHON_CMD=python"
        goto :python_ok
    )
)

echo   Bitte installiere Python manuell: https://www.python.org/downloads/
pause
exit /b 1

:python_ok

REM ══════════════════════════════════════════════════════════════════════
REM  Launch Options laden (launch_options.txt im Root)
REM ══════════════════════════════════════════════════════════════════════

set "LAUNCH_OPTS="
set "LAUNCH_FILE=%ROOT%\launch_options.txt"

if exist "%LAUNCH_FILE%" (
    for /f "usebackq eol=# tokens=*" %%a in ("%LAUNCH_FILE%") do (
        if not "%%a"=="" (
            if defined LAUNCH_OPTS (
                set "LAUNCH_OPTS=!LAUNCH_OPTS! %%a"
            ) else (
                set "LAUNCH_OPTS=%%a"
            )
        )
    )
)

REM ══════════════════════════════════════════════════════════════════════
REM  App starten (init.py → installiert bei Bedarf → startet app.py)
REM ══════════════════════════════════════════════════════════════════════

"%PYTHON_CMD%" "%INIT%" %* !LAUNCH_OPTS!

if errorlevel 1 (
    echo.
    echo Ein Fehler ist aufgetreten!
    pause
) else (
    exit
)