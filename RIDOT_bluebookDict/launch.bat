@echo off
setlocal

REM Get the full path to the venv Scripts folder
set "VENV_SCRIPTS=.\venv\Scripts"

REM Check if we're already inside the virtual environment
if defined VIRTUAL_ENV (
    echo [INFO] Already inside virtual environment.
) else (
    echo [INFO] Not in virtual environment. Launching in new CMD...

    REM Start a new window with the venv activated and run run.py
    start "" cmd /k "%VENV_SCRIPTS%\activate.bat && pip install -r requirements.txt && python run.py"
    
    REM Close this original window
    exit /b
)

REM If already in venv, just run the app
echo [INFO] Starting app inside virtual environment...
python run.py
