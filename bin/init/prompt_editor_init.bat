@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  PersonaUI - Prompt Editor Wrapper
REM  This file is converted to .exe and calls bin\prompt_editor.bat.
REM  This way prompt_editor.bat can be modified anytime without rebuilding the EXE.
REM ══════════════════════════════════════════════════════════════════════

REM Resolve path to project root (EXE sits in root folder)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM Check if bin\prompt_editor.bat exists
if not exist "%ROOT%\bin\prompt_editor.bat" (
    echo [ERROR] bin\prompt_editor.bat not found!
    echo Make sure the EXE is in the PersonaUI root folder.
    timeout /t 10 >nul
    exit /b 1
)

REM Launch prompt_editor.bat in its own window, this wrapper exits silently
start "PersonaUI Prompt Editor" "%ROOT%\bin\prompt_editor.bat"
