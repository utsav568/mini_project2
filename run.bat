@echo off
title GuardianNodes RoadSoS - Emergency Response Ecosystem
echo =====================================================================
echo  🚨 Starting GuardianNodes RoadSoS AI Emergency Response Ecosystem...
echo =====================================================================
echo.

cd /d "%~dp0"

if exist "roadsafety\venv\Scripts\python.exe" (
    echo [1/2] Starting Central FastAPI Backend & React Ecosystem (Port 8000)...
    start "RoadSoS Backend & React Apps" cmd /k "roadsafety\venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir roadsafety --port 8000 --host 0.0.0.0"
    
    echo [2/2] Starting Tactical Streamlit Control Room CAD (Port 8501)...
    start "RoadSoS Control Room CAD" cmd /k "roadsafety\venv\Scripts\streamlit.exe run roadsafety\app.py --server.port 8501"

    timeout /t 3 /nobreak >nul
    echo.
    echo [OK] Ecosystem launched successfully!
    echo - Public App / Driver PWA / Hospital Portal: http://localhost:8000
    echo - Emergency Control Room CAD:               http://localhost:8501
    start http://localhost:8000
    start http://localhost:8501
) else (
    echo [ERROR] Virtual environment not found at roadsafety\venv.
)

pause
