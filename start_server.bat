@echo off
set SCRIPTPATH=%~dp0

REM Check if the virtual environment directory exists
if exist "%SCRIPTPATH%env\.venv\" (
    echo Environment found. Activating...
    call "%SCRIPTPATH%env\.venv\Scripts\activate.bat"
) else (
    echo Environment not found. Creating a new one...
    python -m venv "%SCRIPTPATH%env\.venv"
    call "%SCRIPTPATH%env\.venv\Scripts\activate.bat"
    pip install -r "%SCRIPTPATH%env\requirements.txt"
)

REM Execute the server
cd src
python server.py
echo Press any key to exit
pause