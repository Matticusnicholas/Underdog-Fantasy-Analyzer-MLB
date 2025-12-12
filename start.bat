@echo off
title Fantasy Analyzer - MLB Best Ball
color 0B

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║         Fantasy Analyzer - MLB Best Ball                  ║
echo ║              Starting Web Application...                  ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

:: Find Python - prefer stable versions (3.12, 3.11) over bleeding edge (3.14)
set PYTHON_CMD=

:: Method 1: Try 'py' launcher with specific stable versions first
:: Python 3.14 is in development and lacks pre-built packages
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.12
    goto :found_python
)

py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.11
    goto :found_python
)

py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.13
    goto :found_python
)

py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.10
    goto :found_python
)

:: Method 2: Try common installation paths (prefer stable versions)
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python313\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        set PYTHON_CMD=%%P
        goto :found_python
    )
)

:: Method 3: Try generic 'py' launcher (may pick 3.14)
py --version >nul 2>&1
if not errorlevel 1 (
    echo [WARN] Using default Python version. If install fails, install Python 3.12.
    set PYTHON_CMD=py
    goto :found_python
)

:: Method 4: Try 'python' from PATH (may pick 3.14)
python --version >nul 2>&1
if not errorlevel 1 (
    echo [WARN] Using Python from PATH. If install fails, install Python 3.12.
    set PYTHON_CMD=python
    goto :found_python
)

:: Python not found
echo [ERROR] Python not found!
echo.
echo Please install Python 3.12 from https://python.org
echo (Python 3.14 is in development and lacks pre-built packages)
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:found_python
echo [OK] Found Python: %PYTHON_CMD%

:: Delete old venv if it exists (in case it was created with wrong Python version)
if exist "venv\pyvenv.cfg" (
    findstr /C:"3.14" "venv\pyvenv.cfg" >nul 2>&1
    if not errorlevel 1 (
        echo [WARN] Existing venv uses Python 3.14. Recreating with stable version...
        rmdir /s /q venv
    )
)

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
    pip install --only-binary :all: numpy pandas 2>nul
    if errorlevel 1 (
        echo [WARN] Pre-built numpy/pandas not available for this Python version.
        echo [WARN] Trying with compilation... (requires Visual Studio Build Tools)
    )
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements.
        echo.
        echo TIP: If you see compilation errors, install Python 3.12 from python.org
        echo      Python 3.14 is in development and many packages lack pre-built wheels.
        echo.
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
