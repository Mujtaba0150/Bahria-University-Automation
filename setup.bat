@echo off
setlocal enabledelayedexpansion

rem Resolve script directory (independent of current working directory)
set "SCRIPT_DIR=%~dp0"
set "PYTHON_CMD="

rem Check if Python already exists
where python >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
	where py >nul 2>&1 && set "PYTHON_CMD=py -3"
)

rem Install Python only if missing
if not defined PYTHON_CMD (
	where winget >nul 2>&1
	if errorlevel 1 (
		echo winget not found. Install Python manually and re-run this script.
		pause
		exit /b 1
	)

	echo Installing Python via winget...
	winget install -e --id Python.Python --source winget --accept-source-agreements --accept-package-agreements

	rem Re-check python after install
	where python >nul 2>&1 && set "PYTHON_CMD=python"
	if not defined PYTHON_CMD (
		where py >nul 2>&1 && set "PYTHON_CMD=py -3"
	)
)

if not defined PYTHON_CMD (
	echo Python was not found on PATH. Please reopen your terminal or add it to PATH, then re-run.
	pause
	exit /b 1
)

echo Upgrading pip and installing requirements...
"!PYTHON_CMD!" -m pip install --upgrade pip
"!PYTHON_CMD!" -m pip install -r "%SCRIPT_DIR%requirements.txt"

cls

rem Collect environment variables from user
set /p ENROLLMENT_NUMBER=Enter your ENROLLMENT_NUMBER: 
set /p PASSWORD=Enter your PASSWORD: 
set /p USER_DATA_DIR=Enter your USER_DATA_DIR (absolute path for Playwright profile): 
set /p DOWNLOAD_DIR=Enter your DOWNLOAD_DIR (where assignments will be saved): 
set /p DISABLED=Enter DISABLED (0 for No, 1 for Yes): 
set /p GENDER=Enter GENDER (0=Male, 1=Female): 
set /p AGE=Enter AGE group (0=>22, 1=22-29, 2=>29): 
set /p ON_CAMPUS=Enter ON_CAMPUS (1=On campus, 0=Off campus): 

echo Writing .env file...
(
	echo ENROLLMENT_NUMBER=!ENROLLMENT_NUMBER!
	echo PASSWORD=!PASSWORD!
	echo USER_DATA_DIR=!USER_DATA_DIR!
	echo DOWNLOAD_DIR=!DOWNLOAD_DIR!
	echo DISABLED=!DISABLED!
	echo GENDER=!GENDER!
	echo AGE=!AGE!
	echo ON_CAMPUS=!ON_CAMPUS!
) > "%SCRIPT_DIR%.env"

cls

echo.
set /p CREATE_ALIASES=Do you want to create command aliases for the scripts? (y/n): 

if /i "!CREATE_ALIASES!"=="y" (
	echo.
	echo === Alias setup ===

	set /p ASSIGNMENTS_ALIAS=Enter command alias for checkAssignments.py: 
	set /p ATTENDANCE_ALIAS=Enter command alias for checkAttendance.py: 
	set /p SURVEYS_ALIAS=Enter command alias for fillSurveys.py: 

	rem Create alias for checkAssignments.py
	(
		echo @echo off
		echo "%PYTHON_CMD%" "%SCRIPT_DIR%checkAssignments.py" %%*
	) > "%SCRIPT_DIR%!ASSIGNMENTS_ALIAS!.cmd"

	rem Create alias for checkAttendance.py
	(
		echo @echo off
		echo "%PYTHON_CMD%" "%SCRIPT_DIR%checkAttendance.py" %%*
	) > "%SCRIPT_DIR%!ATTENDANCE_ALIAS!.cmd"

	rem Create alias for fillSurveys.py
	(
		echo @echo off
		echo "%PYTHON_CMD%" "%SCRIPT_DIR%fillSurveys.py" %%*
	) > "%SCRIPT_DIR%!SURVEYS_ALIAS!.cmd"

	echo.
	echo Aliases created successfully:
	echo   !ASSIGNMENTS_ALIAS!
	echo   !ATTENDANCE_ALIAS!
	echo   !SURVEYS_ALIAS!
) else (
	echo Skipping alias creation.
)

echo.
rem Ask user about installation scope
echo Do you want to install scripts for:
echo [1] Current user only
echo [2] All users (requires administrator privileges)
set /p INSTALL_SCOPE=Enter your choice (1 or 2): 

if "!INSTALL_SCOPE!"=="2" (
	echo Adding script directory to system PATH (requires admin)...
	powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \"[Environment]::SetEnvironmentVariable(''Path'', [Environment]::GetEnvironmentVariable(''Path'', ''Machine'') + '';%SCRIPT_DIR%'', ''Machine'')\"' -Verb RunAs"
	echo System PATH updated. Restart your terminal to apply changes.
) else (
	echo Adding script directory to user PATH...
	setx PATH "%%PATH%%;%SCRIPT_DIR%" >nul
	echo User PATH updated. Restart your terminal to apply changes.
)

echo.
echo Setup complete.

pause
