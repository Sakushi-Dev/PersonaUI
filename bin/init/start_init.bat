::[Bat To Exe Converter]
::
::fBE1pAF6MU+EWGLUrBhlfkEEFUSyEVb6b5YO7env5uSA4mglcYI=
::fBE1pAF6MU+EWGLUrBhlfkEEFUSyEVb6b5MV5O317ueC+A0+Dt4Ka4rJyYi9IekL8nnAcIUmwnVKpPseAxFdfQa4Uig9vUZXtFi1MtWPvAHgf2G29E40HnZ9gG3svC4pc9xmm/YqnSWm+S0=
::fBE1pAF6MU+EWGLUrBhlfkEEFUSyEVb6b5MT+uX6+7DH8R9ddusrOJOb7b2AJO8E+QWsXJg732lTmscJRXs=
::fBE1pAF6MU+EWGLUrBhlfkEFHESyEVb6b5QY7OH16KqOoUITDqIcIrPuybGcM9wg60z8baoJ02lRjMQcMCtKcRiubRsnlUlLokyQNfusth3yRUaI02IPCWBwgnDZiyUHYtpmpsIQwCWq73HvmrcD3nb+YbwHW2rizuImdokv1mo=
::fBE1pAF6MU+EWGLUrBhlfkEFHESyEVb6b5QY7OH16KqVp14SQfA8fZyVlPrOD8tz
::fBE1pAF6MU+EWGLUrBhlfkEFHESyEVb6b4UO5+v+/PnHpEQTXfE3fYu7
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFChVRRyaAE+/Fb4I5/jH3/iIqEgeQPEDX4bP8qGMHNAW+Fbre5cY/0VInc8JHxJfcC6pZwEIqH1Rs3CWC9eZoRzuREm280J+EmZ75w==
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
::Zh4grVQjdCyDJGyX8VAjFChVRRyaAE+/Fb4I5/jH3/iIqEgeQPEDX4bP8qGMHNAW+Fbre5cY/0VInc8JHxJfcC6bax0npmBDg03LMt+Z0w==
::YB416Ek+ZG8=
::
::
::978f952a14a936cc963da21a135fa983
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
