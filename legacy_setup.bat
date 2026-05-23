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
    "%%P" -m pip --version >nul 2>&1
    if !errorlevel! == 0 (
        set "PYTHON_CMD=%%P"
        goto FOUND_PYTHON
    )
)

rem Look through py launcher
for /f "delims=" %%P in ('where py 2^>nul') do (
    "%%P" -3 -m pip --version >nul 2>&1
    if !errorlevel! == 0 (
        set "PYTHON_CMD=%%P -3"
        goto FOUND_PYTHON
    )
)

:FOUND_PYTHON
if defined PYTHON_CMD (
    echo Using Python: !PYTHON_CMD!
) else (
    rem Install via winget if no Python with pip found
    echo No Python with pip found, installing via winget...
    where winget >nul 2>&1 || (
        echo winget not found. Install Python manually and re-run.
        pause
        exit /b 1
    )
    winget install -e --id Python.Python --accept-source-agreements --accept-package-agreements

    rem Re-check python after install
    for /f "delims=" %%P in ('where python 2^>nul') do (
        "%%P" -m pip --version >nul 2>&1
        if !errorlevel! == 0 set "PYTHON_CMD=%%P"
    )
    if not defined PYTHON_CMD (
        echo Python installed but pip still not found. Exiting.
        pause
        exit /b 1
    )
    echo Using Python: !PYTHON_CMD!
)

rem ==================================================
rem Upgrade pip and install requirements
rem ==================================================
echo Upgrading pip and installing requirements...
"!PYTHON_CMD!" -m pip install --upgrade pip
"!PYTHON_CMD!" -m pip install -r "!SCRIPT_DIR!\requirements.txt"
python -m playwright install chromium

cls

rem ==================================================
rem Collect environment variables
rem ==================================================
set /p ENROLLMENT_NUMBER=Enter your ENROLLMENT_NUMBER: 
set /p PASSWORD=Enter your PASSWORD: 
set /p USER_DATA_DIR=Enter USER_DATA_DIR (default C:\Users\%USERNAME%\.AppData\Local\ms-playwright): 
if not defined USER_DATA_DIR set "USER_DATA_DIR=C:\Users\%USERNAME%\.AppData\Local\ms-playwright"
set /p DOWNLOAD_DIR=Enter DOWNLOAD_DIR (default C:\Users\%USERNAME%\Documents\Assignments): 
if not defined DOWNLOAD_DIR set "DOWNLOAD_DIR=C:\Users\%USERNAME%\Documents\Assignments"

set /p INSTITUTION=Enter INSTITUTION (default 6): 
if not defined INSTITUTION set INSTITUTION=6

set /p DISABLED=Enter DISABLED (0/1, default 0): 
if not defined DISABLED set DISABLED=0

set /p GENDER=Enter GENDER (0=Male,1=Female, default 0): 
if not defined GENDER set GENDER=0

set /p AGE=Enter AGE (0=<22,1=22-29,2=>29, default 0): 
if not defined AGE set AGE=0

set /p ON_CAMPUS=Enter ON_CAMPUS (1/0, default 1): 
if not defined ON_CAMPUS set ON_CAMPUS=1

echo.
echo NOTIFICATION_LEVEL:
echo   0 = Due Today
echo   1 = Next 4 days
echo   2 = 7 days
echo   3 = 14 days
echo   4 = All
set /p NOTIFICATION_LEVEL=Enter (0-4, default 0): 
if not defined NOTIFICATION_LEVEL set NOTIFICATION_LEVEL=0

set /p NOTIFY_SUBMITTED=Notify submitted? (0/1, default 1): 
if not defined NOTIFY_SUBMITTED set NOTIFY_SUBMITTED=1

rem ==================================================
rem Write .env file
rem ==================================================
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
) > "!SCRIPT_DIR!\.env"

cls

rem ==================================================
rem Alias creation
rem ==================================================
set /p CREATE_ALIASES=Create command aliases? (y/n): 
if /i not "!CREATE_ALIASES!"=="y" goto PATH_SETUP

echo.
set /p ASSIGNMENTS_ALIAS=Alias for checkAssignments.py: 
set /p ATTENDANCE_ALIAS=Alias for checkAttendance.py: 
set /p SURVEYS_ALIAS=Alias for fillSurveys.py: 

echo @echo off > "!SCRIPT_DIR!\!ASSIGNMENTS_ALIAS!.cmd"
echo "!PYTHON_CMD!" "!SCRIPT_DIR!\checkAssignments.py" %%* >> "!SCRIPT_DIR!\!ASSIGNMENTS_ALIAS!.cmd"

echo @echo off > "!SCRIPT_DIR!\!ATTENDANCE_ALIAS!.cmd"
echo "!PYTHON_CMD!" "!SCRIPT_DIR!\checkAttendance.py" %%* >> "!SCRIPT_DIR!\!ATTENDANCE_ALIAS!.cmd"

echo @echo off > "!SCRIPT_DIR!\!SURVEYS_ALIAS!.cmd"
echo "!PYTHON_CMD!" "!SCRIPT_DIR!\fillSurveys.py" %%* >> "!SCRIPT_DIR!\!SURVEYS_ALIAS!.cmd"

echo Aliases created:
echo   !ASSIGNMENTS_ALIAS!
echo   !ATTENDANCE_ALIAS!
echo   !SURVEYS_ALIAS!

rem ==================================================
rem PATH setup
rem ==================================================
:PATH_SETUP
echo.
echo Install scripts for:
echo [1] Current user
echo [2] All users (admin)
set /p INSTALL_SCOPE=Choice (1/2): 

if "!INSTALL_SCOPE!"=="2" goto PATH_MACHINE
goto PATH_USER

:PATH_USER
echo Adding to USER PATH using PowerShell...

set "PSFILE=!SCRIPT_DIR!\update_user_path.ps1"
if exist "!PSFILE!" del "!PSFILE!" >nul 2>&1

>> "!PSFILE!" echo $dir = '!SCRIPT_DIR!'
>> "!PSFILE!" echo $path = [Environment]::GetEnvironmentVariable('Path','User')
>> "!PSFILE!" echo if ($path -notlike "*$dir*") {
>> "!PSFILE!" echo   [Environment]::SetEnvironmentVariable('Path', "$path;$dir", 'User')
>> "!PSFILE!" echo }
>> "!PSFILE!" echo Remove-Item -LiteralPath "$PSScriptRoot\update_user_path.ps1" -Force

powershell -NoProfile -ExecutionPolicy Bypass -File "!PSFILE!"

echo User PATH updated. Restart terminal.
goto DONE

:PATH_MACHINE
echo Creating temporary PowerShell script in script directory...

set "PSFILE=!SCRIPT_DIR!\update_machine_path.ps1"
if exist "!PSFILE!" del "!PSFILE!" >nul 2>&1

>> "!PSFILE!" echo $dir = '!SCRIPT_DIR!'
>> "!PSFILE!" echo $path = [Environment]::GetEnvironmentVariable('Path','Machine')
>> "!PSFILE!" echo if ($path -notlike "*$dir*") {
>> "!PSFILE!" echo   [Environment]::SetEnvironmentVariable('Path', "$path;$dir", 'Machine')
>> "!PSFILE!" echo }
>> "!PSFILE!" echo Remove-Item -LiteralPath "$PSScriptRoot\update_machine_path.ps1" -Force

echo Requesting admin rights...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""!PSFILE!""'"

echo System PATH updated (if UAC was accepted).
goto DONE

:DONE
echo.
echo Setup complete.
pause
