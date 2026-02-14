::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFChVRRyaAE+/Fb4I5/jH//iIqEgeQPEDSIrJybuAIdU61kfte6osxWlfjNgwHh5LewblZww7yQ==
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdCyDJGyX8VAjFChVRRyaAE+/Fb4I5/jH//iIqEgeQPEDSIrJybuAIdU61lfhZpM5mH9Cnas=
::YB416Ek+ZG8=
::
::
::978f952a14a936cc963da21a135fa983
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
