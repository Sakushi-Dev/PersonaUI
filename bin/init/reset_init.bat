@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  PersonaUI - Reset Wrapper
REM  This file is converted to .exe and calls bin\reset.bat.
REM  This way reset.bat can be modified anytime without rebuilding the EXE.
REM ══════════════════════════════════════════════════════════════════════

REM Resolve path to project root (EXE sits in root folder)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM Check if bin\reset.bat exists
if not exist "%ROOT%\bin\reset.bat" (
    echo [ERROR] bin\reset.bat not found!
    echo Make sure the EXE is in the PersonaUI root folder.
    timeout /t 10 >nul
    exit /b 1
)

REM Launch reset.bat in its own window, this wrapper exits silently
start "PersonaUI Reset" "%ROOT%\bin\reset.bat"
