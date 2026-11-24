@echo off
TITLE GuardianNodes RoadSoS - Complete AI Emergency Response Ecosystem
COLOR 0B
echo ===============================================================================
echo     GUARDIANNODES ROADSOS - AI EMERGENCY RESPONSE ECOSYSTEM (DELHI NCR NODE)
echo ===============================================================================
echo [1/3] Activating Python Virtual Environment...
cd /d "%~dp0"
call roadsafety\venv\Scripts\activate.bat

echo [2/3] Starting Central FastAPI Backend & React Ecosystem (Port 8000)...
start "RoadSoS Central API & Web Portal" cmd /k "roadsafety\venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir roadsafety --port 8000 --host 0.0.0.0"

echo [3/3] Starting Tactical Streamlit Control Room (Port 8501)...
start "RoadSoS Control Room CAD" cmd /k "roadsafety\venv\Scripts\streamlit.exe run roadsafety\app.py --server.port 8501"

timeout /t 3 /nobreak >nul
echo.
echo ===============================================================================
echo   ALL ECOSYSTEM APPLICATIONS ARE RUNNING:
echo   - Public Emergency SOS App:    http://localhost:8000
echo   - Driver CAD Navigation PWA:  http://localhost:8000 (Switch to Driver tab)
echo   - Hospital Management Portal:  http://localhost:8000 (Switch to Hospital tab)
echo   - Central FastAPI Backend API: http://localhost:8000/docs
echo   - Emergency Control Room CAD:  http://localhost:8501
echo ===============================================================================
echo Opening browsers...
start http://localhost:8000
start http://localhost:8501
pause
