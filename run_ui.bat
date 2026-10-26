@echo off
title Vantage XAUUSD Bot Dashboard
cd /d "%~dp0"

echo =======================================================
echo   Vantage XAUUSD Bot - Real-Time Web Dashboard
echo =======================================================
echo.

:: Try python, fallback to py launcher if python isn't directly recognized
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PY_CMD=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PY_CMD=py
    ) else (
        echo [ERROR] Python was not found in PATH!
        echo Please ensure Python 3.11 is installed.
        pause
        exit /b 1
    )
)

echo [1/2] Checking web dependencies (FastAPI, Uvicorn)...
%PY_CMD% -m pip install -r requirements.txt --quiet

echo [2/2] Launching Web Dashboard on http://localhost:8000 ...
echo (Your web browser will open automatically in a moment)
echo.
echo Press Ctrl+C in this window when you want to stop the server.
echo =======================================================
echo.

%PY_CMD% web_app.py
pause

