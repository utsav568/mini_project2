@echo off
title GuardianNodes RoadSoS - Emergency CAD Platform
echo =====================================================================
echo  🚨 Starting GuardianNodes RoadSoS CAD Command Center...
echo =====================================================================
echo.

cd /d "%~dp0"

if exist "venv\Scripts\streamlit.exe" (
    echo [OK] Virtual environment detected.
    echo [OK] Launching Streamlit Application...
    echo.
    "venv\Scripts\streamlit.exe" run app.py
) else (
    echo [WARN] Local venv not found, trying system streamlit...
    streamlit run app.py
)

pause
