#!/bin/bash
# Startup script for GuardianNodes RoadSoS
echo "=== Starting GuardianNodes RoadSoS Ecosystem ==="

# 1. Start FastAPI backend & React apps in background
echo "[1/2] Starting Central FastAPI Backend (:8000)..."
python -m uvicorn backend.main:app --app-dir roadsafety --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to initialize
sleep 3

# 2. Start Streamlit Command CAD in foreground
echo "[2/2] Starting Streamlit CAD Control Room (:8501)..."
streamlit run roadsafety/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false

# If Streamlit exits, kill FastAPI
kill $FASTAPI_PID
