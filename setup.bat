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
set /p INSTITUTION=Enter INSTITUTION selection (default 6): 
if not defined INSTITUTION set INSTITUTION=6
set /p DISABLED=Enter DISABLED (0 = No, 1 = Yes): 
if not defined DISABLED set DISABLED=0
set /p GENDER=Enter GENDER (0 = Male, 1 = Female): 
if not defined GENDER set GENDER=0
set /p AGE=Enter AGE group (0 = <22, 1 = 22-29, 2 = >29): 
if not defined AGE set AGE=0
set /p ON_CAMPUS=Enter ON_CAMPUS (1 = On campus, 0 = Off campus): 
if not defined ON_CAMPUS set ON_CAMPUS=1
echo.
echo NOTIFICATION_LEVEL options:
echo   0 = Due Today
echo   1 = Up to next 4 days
echo   2 = Up to 7 days
echo   3 = Up to 14 days
echo   4 = All notifications
set /p NOTIFICATION_LEVEL=Enter NOTIFICATION_LEVEL (0-4, default 0): 
if not defined NOTIFICATION_LEVEL set NOTIFICATION_LEVEL=0
set /p NOTIFY_SUBMITTED=Enter NOTIFY_SUBMITTED (0 = No, 1 = Yes, default 1): 
if not defined NOTIFY_SUBMITTED set NOTIFY_SUBMITTED=1

echo Writing .env file...
(
	echo ENROLLMENT_NUMBER=!ENROLLMENT_NUMBER!
	echo PASSWORD=!PASSWORD!
	echo USER_DATA_DIR=!USER_DATA_DIR!
	echo DOWNLOAD_DIR=!DOWNLOAD_DIR!
	echo INSTITUTION=!INSTITUTION!
	echo DISABLED=!DISABLED!
	echo GENDER=!GENDER!
	echo AGE=!AGE!
	echo ON_CAMPUS=!ON_CAMPUS!
	echo NOTIFICATION_LEVEL=!NOTIFICATION_LEVEL!
	echo NOTIFY_SUBMITTED=!NOTIFY_SUBMITTED!
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
