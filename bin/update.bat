@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title PersonaUI - Update
color 0B

echo ╔══════════════════════════════════════════════╗
echo ║         PersonaUI - Update                   ║
echo ╚══════════════════════════════════════════════╝
echo.

REM ----------------------------------------------
REM  Zum Projektverzeichnis wechseln
REM ----------------------------------------------
cd /d "%~dp0.."
echo [INFO] Projektverzeichnis: %CD%
echo.

REM ----------------------------------------------
REM  1. Git prufen
REM ----------------------------------------------
echo [1/5] Prüfe Git...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FEHLER] Git ist nicht installiert oder nicht im PATH!
    echo   Bitte installiere Git: https://git-scm.com/
    goto :error_exit
)
echo   [OK] Git gefunden.
echo.

REM ----------------------------------------------
REM  2. Remote aktualisieren
REM ----------------------------------------------
echo [2/5] Hole neueste Informationen von origin/main...
git fetch origin main
if %errorlevel% neq 0 (
    echo   [FEHLER] Konnte origin/main nicht abrufen!
    echo   Prüfe deine Netzwerkverbindung.
    goto :error_exit
)
echo   [OK] Remote aktualisiert.
echo.

REM ----------------------------------------------
REM  3. Aktuellen und Remote-Stand vergleichen
REM ----------------------------------------------
echo [3/5] Prüfe ob Updates verfügbar sind...

REM Aktuellen main und remote main Hash holen
for /f "tokens=*" %%i in ('git rev-parse origin/main 2^>nul') do set "REMOTE_HASH=%%i"

REM Gespeicherten Commit aus Marker lesen (JSON: update_state.json)
set "MARKER_FILE=%CD%\src\settings\update_state.json"
set "LAST_HASH="
if exist "%MARKER_FILE%" (
    for /f "tokens=2 delims=:" %%i in ('findstr /C:"commit" "%MARKER_FILE%" 2^>nul') do (
        set "RAW=%%i"
    )
    if defined RAW (
        set "RAW=!RAW: =!"
        set "RAW=!RAW:"=!"
        set "RAW=!RAW:}=!"
        set "LAST_HASH=!RAW!"
    )
)

if "!LAST_HASH!"=="!REMOTE_HASH!" (
    echo.
    echo   PersonaUI ist bereits auf dem neuesten Stand!
    echo.
    goto :clean_exit
)

REM Neue Commits zählen
if defined LAST_HASH (
    for /f "tokens=*" %%i in ('git rev-list --count !LAST_HASH!..!REMOTE_HASH! 2^>nul') do set "NEW_COMMITS=%%i"
    echo   [INFO] !NEW_COMMITS! neue Commits verfügbar.
) else (
    echo   [INFO] Erster Update-Lauf.
)
echo.

REM ----------------------------------------------
REM  4. Update durchfuehren: origin/main mergen
REM ----------------------------------------------
echo [4/5] Führe Update durch (merge origin/main)...
echo.

REM Aktuelle Änderungen sichern
git stash --quiet 2>nul

REM origin/main in aktuellen Branch mergen
git merge origin/main --no-edit
if %errorlevel% neq 0 (
    echo.
    echo   [FEHLER] Merge-Konflikt! Bitte manuell lösen.
    echo   Tipp: Löse die Konflikte und führe 'git merge --continue' aus.
    goto :error_exit
)

REM Gestashte Änderungen wiederherstellen (falls vorhanden)
git stash pop --quiet 2>nul

echo   [OK] Code aktualisiert.
echo.

REM ----------------------------------------------
REM  5. Abhaengigkeiten aktualisieren
REM ----------------------------------------------
echo [5/5] Aktualisiere Abhängigkeiten...

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet --upgrade 2>nul
    echo   [OK] Abhängigkeiten aktualisiert.
) else (
    echo   [WARNUNG] Keine virtuelle Umgebung gefunden.
    echo   Führe zuerst bin\install.bat aus.
)
echo.

REM ----------------------------------------------
REM  Marker-Datei aktualisieren (JSON)
REM ----------------------------------------------
>  "%MARKER_FILE%" echo {
>> "%MARKER_FILE%" echo   "commit": "!REMOTE_HASH!"
>> "%MARKER_FILE%" echo }

echo ╔══════════════════════════════════════════════╗
echo ║         Update erfolgreich!                  ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   PersonaUI wurde auf die neueste stabile
echo   Version aktualisiert.
echo.
echo   Starte PersonaUI neu mit: bin\start.bat
echo.
pause
exit /b 0

:error_exit
echo.
echo   Update fehlgeschlagen!
echo.
pause
exit /b 1

:clean_exit
pause
exit /b 0
