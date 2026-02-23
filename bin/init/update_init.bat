@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  PersonaUI - Update Wrapper
REM  This file is converted to .exe and calls bin\update.bat.
REM  This way update.bat can be modified anytime without rebuilding the EXE.
REM ══════════════════════════════════════════════════════════════════════

REM Resolve path to project root (EXE sits in root folder)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM Check if bin\update.bat exists
if not exist "%ROOT%\bin\update.bat" (
    echo [ERROR] bin\update.bat not found!
    echo Make sure the EXE is in the PersonaUI root folder.
    timeout /t 10 >nul
    exit /b 1
)

REM Launch update.bat in its own window, this wrapper exits silently
start "PersonaUI Update" "%ROOT%\bin\update.bat"
