#!/bin/bash
# Startup script for GuardianNodes RoadSoS on Render / Cloud
PORT=${PORT:-8000}
echo "=== Starting GuardianNodes RoadSoS Ecosystem on PORT $PORT ==="

# 1. Start FastAPI backend & React frontend
echo "[1/2] Starting Central FastAPI Backend (:8000 / :$PORT)..."
python -m uvicorn backend.main:app --app-dir roadsafety --host 0.0.0.0 --port $PORT &
FASTAPI_PID=$!

# Wait for FastAPI to initialize
sleep 2

# 2. Start Streamlit Command CAD in background
echo "[2/2] Starting Streamlit CAD Control Room (:8501)..."
streamlit run roadsafety/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# Wait for processes
wait -n
exit $?
