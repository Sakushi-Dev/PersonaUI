@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title PersonaUI - Frontend Build
color 0B

echo ╔══════════════════════════════════════════════╗
echo ║       PersonaUI - Frontend Build              ║
echo ╚══════════════════════════════════════════════╝
echo.

REM ──────────────────────────────────────────────
REM  Pfade bestimmen
REM ──────────────────────────────────────────────

set "SELF_DIR=%~dp0"

REM Skript liegt in src\dev\frontend\ → 3 Ebenen hoch zum Root
if exist "%SELF_DIR%..\..\..\frontend\package.json" (
    set "ROOT=%SELF_DIR%..\..\..\"
) else if exist "%SELF_DIR%src\app.py" (
    set "ROOT=%SELF_DIR%"
) else if exist "%SELF_DIR%..\src\app.py" (
    set "ROOT=%SELF_DIR%.."
) else (
    echo [FEHLER] Projektverzeichnis nicht gefunden!
    pause
    exit /b 1
)

if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "FRONTEND_DIR=%ROOT%\frontend"
set "NODE_DIR=%ROOT%\bin\node"
set "NPM=%NODE_DIR%\npm.cmd"

REM ──────────────────────────────────────────────
REM  1. Frontend-Verzeichnis prüfen
REM ──────────────────────────────────────────────

echo [1/4] Prüfe Frontend-Verzeichnis...

if not exist "%FRONTEND_DIR%\package.json" (
    echo   [FEHLER] frontend\package.json nicht gefunden!
    goto :error_exit
)
echo   [OK] %FRONTEND_DIR%
echo.

REM ──────────────────────────────────────────────
REM  2. Node.js prüfen
REM ──────────────────────────────────────────────

echo [2/4] Prüfe Node.js...

if exist "%NPM%" (
    set "PATH=%NODE_DIR%;%PATH%"
    echo   [OK] Lokales Node.js gefunden.
) else (
    where npm >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [FEHLER] Node.js / npm nicht gefunden!
        echo   Bitte stelle sicher, dass bin\node vorhanden ist.
        goto :error_exit
    )
    echo   [OK] System Node.js gefunden.
)
echo.

REM ──────────────────────────────────────────────
REM  3. Dependencies installieren (falls nötig)
REM ──────────────────────────────────────────────

echo [3/4] Prüfe Dependencies...

cd /d "%FRONTEND_DIR%"

if not exist "node_modules" (
    echo   node_modules fehlt - installiere...
    call npm install
    if !errorlevel! neq 0 (
        echo   [FEHLER] npm install fehlgeschlagen!
        goto :error_exit
    )
    echo   [OK] Dependencies installiert.
) else (
    echo   [OK] node_modules vorhanden.
)
echo.

REM ──────────────────────────────────────────────
REM  4. Build ausführen
REM ──────────────────────────────────────────────

echo [4/4] Baue Frontend (vite build)...
echo.

call npm run build

if %errorlevel% neq 0 (
    echo.
    echo   [FEHLER] Build fehlgeschlagen!
    goto :error_exit
)

echo.
echo ══════════════════════════════════════════════
echo   [OK] Frontend erfolgreich kompiliert!
echo   Output: frontend\dist\
echo ══════════════════════════════════════════════
echo.
exit /b 0

:error_exit
echo.
echo   Build abgebrochen.
pause
exit /b 1
