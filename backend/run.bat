@echo off
:: Safely change to the directory where the script is located
cd /d "%~dp0"

:: Activate the virtual environment
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

:: Install requirements
pip install -r requirements.txt -q

:: Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload