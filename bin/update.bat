@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title PersonaUI - Update
color 0B

REM ----------------------------------------------
REM  Self-copy guard: git merge overwrites this file mid-execution.
REM  CMD reads .bat by byte offset, so a changed file causes random jumps.
REM  Solution: copy to %TEMP% and re-launch from there, passing project dir.
REM ----------------------------------------------
if not defined _PERSONAUI_UPDATE_SAFE (
    set "_PERSONAUI_UPDATE_SAFE=1"
    set "PROJECT_DIR=%~dp0.."
    copy /y "%~f0" "%TEMP%\personaui_update.bat" >nul 2>&1
    call "%TEMP%\personaui_update.bat" "!PROJECT_DIR!"
    set "_EXIT_CODE=!errorlevel!"
    del /q "%TEMP%\personaui_update.bat" >nul 2>&1
    exit /b !_EXIT_CODE!
)

echo ╔══════════════════════════════════════════════╗
echo ║         PersonaUI - Update                   ║
echo ╚══════════════════════════════════════════════╝
echo.

REM ----------------------------------------------
REM  Change to project directory (passed as argument from self-copy)
REM ----------------------------------------------
cd /d "%~1"
echo [INFO] Project directory: %CD%
echo.

REM ----------------------------------------------
REM  1. Check Git
REM ----------------------------------------------
echo [1/6] Checking Git...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] Git is not installed or not in PATH!
    echo   Please install Git: https://git-scm.com/
    goto :error_exit
)
echo   [OK] Git found.
echo.

REM ----------------------------------------------
REM  2. Fetch remote
REM ----------------------------------------------
echo [2/6] Fetching latest information from origin/main...
git fetch origin main
if %errorlevel% neq 0 (
    echo   [ERROR] Could not fetch origin/main!
    echo   Check your network connection.
    goto :error_exit
)
echo   [OK] Remote updated.
echo.

REM ----------------------------------------------
REM  3. Compare versions (uses PowerShell for reliable JSON parsing)
REM ----------------------------------------------
echo [3/6] Checking for updates...

REM Parse local version via PowerShell
set "LOCAL_VERSION="
for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "(Get-Content '%CD%\version.json' -Raw | ConvertFrom-Json).version"`) do (
    set "LOCAL_VERSION=%%v"
)
if not defined LOCAL_VERSION (
    echo   [WARNING] Could not read local version.json
    set "LOCAL_VERSION=unknown"
)
echo   [INFO] Current version: !LOCAL_VERSION!

REM Parse remote version via PowerShell (reads git show output)
set "REMOTE_VERSION="
for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "(git show origin/main:version.json | ConvertFrom-Json).version"`) do (
    set "REMOTE_VERSION=%%v"
)
if not defined REMOTE_VERSION (
    echo   [WARNING] Could not read remote version.
    echo   Update will proceed anyway.
    set "REMOTE_VERSION=unknown"
)
echo   [INFO] Remote version:  !REMOTE_VERSION!

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo.
    echo   PersonaUI is already up to date! ^(v!LOCAL_VERSION!^)
    echo.
    goto :clean_exit
)

echo.
echo   [INFO] New version available: v!REMOTE_VERSION! ^(current: v!LOCAL_VERSION!^)
echo.

REM ----------------------------------------------
REM  4. Perform update: reset to origin/main
REM ----------------------------------------------
echo [4/6] Performing update...
echo.

REM Abort any stuck merge from a previous attempt
git merge --abort >nul 2>&1

REM Reset to remote version (clean update)
git reset --hard origin/main
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Could not reset to origin/main.
    echo   Try deleting the folder and cloning fresh.
    goto :error_exit
)

echo   [OK] Code updated.
echo.

REM ----------------------------------------------
REM  5. Update dependencies
REM ----------------------------------------------
echo [5/6] Updating dependencies...

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet --upgrade 2>nul
    echo   [OK] Dependencies updated.
) else (
    echo   [WARNING] No virtual environment found.
    echo   Run bin\install.bat first.
)
REM ----------------------------------------------
REM  6. Rebuild frontend (so new UI elements land in dist)
REM ----------------------------------------------
echo [6/6] Rebuilding frontend...

if exist "src\dev\frontend\build_frontend.bat" (
    call "src\dev\frontend\build_frontend.bat"
    if !errorlevel! neq 0 (
        echo   [WARNING] Frontend build failed. UI may be outdated.
    )
) else (
    echo   [WARNING] build_frontend.bat not found. Skipping frontend build.
)
echo.

REM ----------------------------------------------
REM  Update state file (version-based)
REM ----------------------------------------------
set "STATE_FILE=%CD%\src\settings\update_state.json"
>  "%STATE_FILE%" echo {
>> "%STATE_FILE%" echo   "version": "!REMOTE_VERSION!"
>> "%STATE_FILE%" echo }

echo ╔══════════════════════════════════════════════╗
echo ║         Update successful!                   ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   PersonaUI has been updated to v!REMOTE_VERSION!
echo.
echo   Restart PersonaUI with: bin\start.bat
echo.
pause
exit /b 0

:error_exit
echo.
echo   Update failed!
echo.
pause
exit /b 1

:clean_exit
pause
exit /b 0
