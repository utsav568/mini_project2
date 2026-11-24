# GuardianNodes RoadSoS - Complete Ecosystem Launcher (PowerShell)
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "    GUARDIANNODES ROADSOS - AI EMERGENCY RESPONSE ECOSYSTEM (DELHI NCR NODE)" -ForegroundColor White
Write-Host "===============================================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot

Write-Host "`n[1/3] Starting Central FastAPI Backend & React Ecosystem on Port 8000..." -ForegroundColor Yellow
Start-Process -FilePath "roadsafety\venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --app-dir roadsafety --port 8000 --host 0.0.0.0"

Write-Host "[2/3] Starting Tactical Streamlit Control Room on Port 8501..." -ForegroundColor Yellow
Start-Process -FilePath "roadsafety\venv\Scripts\streamlit.exe" -ArgumentList "run roadsafety\app.py --server.port 8501"

Start-Sleep -Seconds 3

Write-Host "`n===============================================================================" -ForegroundColor Green
Write-Host "  ALL ECOSYSTEM APPLICATIONS ARE RUNNING:" -ForegroundColor Green
Write-Host "  - Public Emergency SOS App:    http://localhost:8000" -ForegroundColor White
Write-Host "  - Driver CAD Navigation PWA:  http://localhost:8000 (Switch to Driver tab)" -ForegroundColor White
Write-Host "  - Hospital Management Portal:  http://localhost:8000 (Switch to Hospital tab)" -ForegroundColor White
Write-Host "  - Central FastAPI Backend API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Emergency Control Room CAD:  http://localhost:8501" -ForegroundColor White
Write-Host "===============================================================================" -ForegroundColor Green

Start-Process "http://localhost:8000"
Start-Process "http://localhost:8501"
