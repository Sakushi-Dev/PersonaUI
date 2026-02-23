@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  PersonaUI - Start Wrapper
REM  This file is converted to .exe and calls bin\start.bat.
REM  This way start.bat can be modified anytime without rebuilding the EXE.
REM ══════════════════════════════════════════════════════════════════════

REM Resolve path to project root (EXE sits in root folder)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM Check if bin\start.bat exists
if not exist "%ROOT%\bin\start.bat" (
    echo [ERROR] bin\start.bat not found!
    echo Make sure the EXE is in the PersonaUI root folder.
    timeout /t 10 >nul
    exit /b 1
)

REM Launch start.bat in its own window, this wrapper exits silently
start "PersonaUI" "%ROOT%\bin\start.bat"
