@echo off
title Fantasy Analyzer - MLB Best Ball
color 0B

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║         Fantasy Analyzer - MLB Best Ball                  ║
echo ║              Starting Web Application...                  ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

:: Find Python - try multiple methods
set PYTHON_CMD=

:: Method 1: Try 'python' command
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :found_python
)

:: Method 2: Try 'py' launcher (Windows Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :found_python
)

:: Method 3: Try 'python3' command
python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :found_python
)

:: Method 4: Try common installation paths
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "%ProgramFiles%\Python39\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
) do (
    if exist %%P (
        set PYTHON_CMD=%%P
        goto :found_python
    )
)

:: Python not found
echo [ERROR] Python not found!
echo.
echo Please install Python 3.9+ from https://python.org
echo Make sure to check "Add Python to PATH" during installation.
echo.
echo Or, if Python is installed, you can manually set the path:
echo   set PYTHON_CMD="C:\path\to\python.exe"
echo.
pause
exit /b 1

:found_python
echo [OK] Found Python: %PYTHON_CMD%

:: Check if virtual environment exists, create if not
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    %PYTHON_CMD% -m venv venv
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

:: Upgrade pip first to avoid issues
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

:: Check if requirements are installed by testing Flask import
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requirements (this may take a minute)...
    echo [INFO] Using pre-built packages to avoid compilation...
    pip install --only-binary :all: numpy pandas >nul 2>&1
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Some packages may need manual install. Trying alternative...
        pip install --prefer-binary -r requirements.txt
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
