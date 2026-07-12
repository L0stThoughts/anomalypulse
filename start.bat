@echo off
REM Starting AnomalyPulse...

REM Safely change to the directory where the script is located
cd /d "%~dp0"

REM Start backend in a new window
echo Starting Backend...
start "AnomalyPulse Backend" cmd /c "cd backend && call run.bat"

REM Sleep for 3 seconds
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo Starting Frontend...
start "AnomalyPulse Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo --- AnomalyPulse is Running ---
echo Backend: http://localhost:8080
echo Frontend: http://localhost:5173
echo -------------------------------
echo.
echo [To stop the servers, close their respective command prompt windows.]
pause