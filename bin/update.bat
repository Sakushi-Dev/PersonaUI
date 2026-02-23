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
REM  Change to project directory
REM ----------------------------------------------
cd /d "%~dp0.."
echo [INFO] Project directory: %CD%
echo.

REM ----------------------------------------------
REM  1. Check Git
REM ----------------------------------------------
echo [1/5] Checking Git...
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
echo [2/5] Fetching latest information from origin/main...
git fetch origin main
if %errorlevel% neq 0 (
    echo   [ERROR] Could not fetch origin/main!
    echo   Check your network connection.
    goto :error_exit
)
echo   [OK] Remote updated.
echo.

REM ----------------------------------------------
REM  3. Compare versions
REM ----------------------------------------------
echo [3/5] Checking for updates...

REM Read local version from version.json
set "VERSION_FILE=%CD%\version.json"
set "LOCAL_VERSION="
if exist "%VERSION_FILE%" (
    for /f "tokens=2 delims=:" %%i in ('findstr /C:"version" "%VERSION_FILE%" 2^>nul') do (
        set "RAW=%%i"
    )
    if defined RAW (
        set "RAW=!RAW: =!"
        set "RAW=!RAW:"=!"
        set "RAW=!RAW:}=!"
        set "RAW=!RAW:,=!"
        set "LOCAL_VERSION=!RAW!"
    )
)

if not defined LOCAL_VERSION (
    echo   [WARNING] Could not read local version.json
    set "LOCAL_VERSION=unknown"
)
echo   [INFO] Current version: !LOCAL_VERSION!

REM Read remote version from origin/main:version.json
set "REMOTE_VERSION="
for /f "tokens=*" %%i in ('git show origin/main:version.json 2^>nul') do (
    echo %%i | findstr /C:"version" >nul 2>&1
    if !errorlevel! equ 0 (
        set "RAWLINE=%%i"
    )
)
if defined RAWLINE (
    for /f "tokens=2 delims=:" %%i in ("!RAWLINE!") do (
        set "RAW2=%%i"
    )
    if defined RAW2 (
        set "RAW2=!RAW2: =!"
        set "RAW2=!RAW2:"=!"
        set "RAW2=!RAW2:}=!"
        set "RAW2=!RAW2:,=!"
        set "REMOTE_VERSION=!RAW2!"
    )
)

if not defined REMOTE_VERSION (
    echo   [WARNING] Could not read remote version.
    echo   Update will proceed anyway.
    set "REMOTE_VERSION=unknown"
)
echo   [INFO] Remote version:  !REMOTE_VERSION!

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo.
    echo   PersonaUI is already up to date! (v!LOCAL_VERSION!)
    echo.
    goto :clean_exit
)

echo   [INFO] New version available: v!REMOTE_VERSION! (current: v!LOCAL_VERSION!)
echo.

REM ----------------------------------------------
REM  4. Perform update: merge origin/main
REM ----------------------------------------------
echo [4/5] Performing update (merge origin/main)...
echo.

REM Stash current changes
git stash --quiet 2>nul

REM Merge origin/main into current branch
git merge origin/main --no-edit
if %errorlevel% neq 0 (
    echo.
    echo   [ERROR] Merge conflict! Please resolve manually.
    echo   Tip: Resolve the conflicts and run 'git merge --continue'.
    goto :error_exit
)

REM Restore stashed changes (if any)
git stash pop --quiet 2>nul

echo   [OK] Code updated.
echo.

REM ----------------------------------------------
REM  5. Update dependencies
REM ----------------------------------------------
echo [5/5] Updating dependencies...

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet --upgrade 2>nul
    echo   [OK] Dependencies updated.
) else (
    echo   [WARNING] No virtual environment found.
    echo   Run bin\install.bat first.
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
