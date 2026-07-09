@echo off
setlocal EnableDelayedExpansion

rem ==================================================
rem Resolve script directory
rem ==================================================
set "SCRIPT_DIR=%~dp0"
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

rem ==================================================
rem Find Python with pip
rem ==================================================
set "PYTHON_CMD="

rem Look through all python executables
for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | findstr /i "mingw msys" >nul
    if errorlevel 1 (
        "%%P" -m pip --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD=%%P"
            goto FOUND_PYTHON
        )
    )
)

rem Look through py launcher
for /f "delims=" %%P in ('where py 2^>nul') do (
    echo %%P | findstr /i "mingw msys" >nul
    if errorlevel 1 (
        "%%P" -3 -m pip --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD=%%P -3"
            goto FOUND_PYTHON
        )
    )
)

:FOUND_PYTHON
if defined PYTHON_CMD (
    echo Using Python: !PYTHON_CMD!
) else (
    rem Install via winget if no Python with pip found
    echo No Python with pip found. Installing via winget...

    where winget >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: winget not found. Please install Python manually:
        echo https://www.python.org/downloads/
        echo.
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )

    echo Installing Python...
    winget install -i --id Python.Python --accept-source-agreements --accept-package-agreements

    rem Re-check python after install
    for /f "delims=" %%P in ('where python 2^>nul') do (
        "%%P" -m pip --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD=%%P"
            goto PYTHON_INSTALLED
        )
    )

    :PYTHON_INSTALLED
    if not defined PYTHON_CMD (
        echo.
        echo ERROR: Python installed but pip still not found.
        echo Please ensure Python is in your PATH and try again.
        pause
        exit /b 1
    )

    echo Using Python: !PYTHON_CMD!
)

rem ==================================================
rem Verify Python version
rem ==================================================
for /f "delims=" %%V in ('
    !PYTHON_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul
') do set "PYTHON_VERSION=%%V"

echo Python version: !PYTHON_VERSION!

rem ==================================================
rem Upgrade pip and install requirements
rem ==================================================
echo.
echo Installing/upgrading pip, setuptools, and wheel...
call !PYTHON_CMD! -m pip install --upgrade pip setuptools wheel

echo.
echo Installing requirements...
call !PYTHON_CMD! -m pip install -r "!SCRIPT_DIR!\requirements.txt"

echo.
echo Installing Playwright browsers...
call !PYTHON_CMD! -m playwright install chromium

cls

rem ==================================================
rem Run setup GUI
rem ==================================================
echo Launching setup wizard...
cd /d "!SCRIPT_DIR!"
call !PYTHON_CMD! setup_gui.py

if !errorlevel! == 0 (
    echo.
    echo Setup completed successfully!
    echo Your .env file has been created.
    echo.
    echo You can now run the scripts:
    echo   python checkAssignments.py
    echo   python checkAttendance.py
    echo   python fillSurveys.py
    echo.
) else (
    echo.
    echo Setup wizard was cancelled or encountered an error.
    pause
    exit /b 1
)

pause