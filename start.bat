@echo off
title Fantasy Analyzer - MLB Best Ball
color 0B

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║         Fantasy Analyzer - MLB Best Ball                  ║
echo ║              Starting Web Application...                  ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: Check if virtual environment exists, create if not
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Check if requirements are installed by testing Flask import
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
    echo [OK] Requirements installed.
) else (
    echo [OK] Requirements already installed.
)

:: Install package in development mode if not already
python -c "import analyzer" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing package...
    pip install -e . >nul 2>&1
    echo [OK] Package installed.
)

:: Create data directories if they don't exist
if not exist "data" mkdir data
if not exist "data\screenshots" mkdir data\screenshots
if not exist "data\exports" mkdir data\exports

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║  Starting server at http://localhost:5000                 ║
echo ║  Press Ctrl+C to stop the server                          ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

:: Start the web application
python run_web.py

:: Deactivate on exit
call venv\Scripts\deactivate.bat
pause
