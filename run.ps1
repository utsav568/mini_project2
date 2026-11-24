Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " 🚨 Starting GuardianNodes RoadSoS AI Emergency Response Ecosystem..." -ForegroundColor White
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPython = Join-Path $scriptDir "roadsafety\venv\Scripts\python.exe"
$venvStreamlit = Join-Path $scriptDir "roadsafety\venv\Scripts\streamlit.exe"

if (Test-Path $venvPython) {
    Write-Host "[1/2] Starting Central FastAPI Backend & React Ecosystem (Port 8000)..." -ForegroundColor Yellow
    Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn backend.main:app --app-dir roadsafety --port 8000 --host 0.0.0.0"

    Write-Host "[2/2] Starting Tactical Streamlit Control Room CAD (Port 8501)..." -ForegroundColor Yellow
    Start-Process -FilePath $venvStreamlit -ArgumentList "run roadsafety\app.py --server.port 8501"

    Start-Sleep -Seconds 3
    Write-Host "`n[OK] Ecosystem launched successfully!" -ForegroundColor Green
    Write-Host " - Public App / Driver PWA / Hospital Portal: http://localhost:8000" -ForegroundColor White
    Write-Host " - Emergency Control Room CAD:               http://localhost:8501" -ForegroundColor White

    Start-Process "http://localhost:8000"
    Start-Process "http://localhost:8501"
} else {
    Write-Host "[ERROR] Virtual environment not found at roadsafety\venv" -ForegroundColor Red
}
