"""
roadsafety/backend/main.py
==========================
Central FastAPI Backend for the GuardianNodes RoadSoS Emergency Response Ecosystem.
Connects the Public Citizen App, Control Room, Driver PWA, and Hospital Management Portal.
"""

import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base, SessionLocal, DATA_DIR, BASE_DIR
from .models import User, Hospital, Vehicle, V2XMeshNode, Incident, AIAnalysis
from .security import hash_password
from .websocket_manager import ws_manager

from .routers import (
    auth, incidents, vehicles, hospitals,
    ai, routing, mesh, analytics
)

logger = logging.getLogger("roadsafety.backend")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="GuardianNodes RoadSoS - Emergency Response Ecosystem API",
    description="Central API & WebSocket telemetry gateway connecting Public Reporting, CAD Control Room, Driver PWA, and Hospital Portals.",
    version="2.5.0",
)

# CORS configuration allowing all local development ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all modular routers
app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(vehicles.router)
app.include_router(hospitals.router)
app.include_router(ai.router)
app.include_router(routing.router)
app.include_router(mesh.router)
app.include_router(analytics.router)

# Mount evidence static files
evidence_dir = DATA_DIR / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time bi-directional WebSocket telemetry connection."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive and incoming message listening
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # If driver sends GPS ping over WebSocket
                if msg.get("type") == "DRIVER_PING":
                    await ws_manager.broadcast("DRIVER_GPS_UPDATED", msg.get("data", {}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket client error: {exc}")
        ws_manager.disconnect(websocket)


@app.get("/api/health")
def health_check():
    """Health check endpoint for production monitors and load balancers."""
    return {
        "status": "healthy",
        "service": "GuardianNodes RoadSoS Central API",
        "version": "2.5.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": engine.name,
    }


# Mount built React frontend if dist directory exists (mounted last to avoid shadowing API & WebSocket routes)
frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    from fastapi.responses import HTMLResponse
    @app.get("/", response_class=HTMLResponse)
    def index_fallback():
        return """<!DOCTYPE html><html><head><title>GuardianNodes RoadSoS</title></head><body style="font-family:sans-serif;background:#0f172a;color:#f8fafc;padding:40px;text-align:center;"><h1>🚨 GuardianNodes RoadSoS Ecosystem</h1><p>Central API Gateway is Online.</p><p><a href="/docs" style="color:#38bdf8;font-size:18px;">Open Interactive API Docs &rarr;</a></p></body></html>"""


@app.on_event("startup")
def startup_seed_database():
    """Ensure database schema is created and seed master records if empty."""
    from .migrate_db import run_migrations
    run_migrations()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed Users if empty
        if db.query(User).count() == 0:
            seed_users = [
                User(username="admin", password_hash=hash_password("admin123"), full_name="Commander Rohit Singh", role="SUPER_ADMIN", badge_number="GN-CMD-01", phone="+91 98100 00001"),
                User(username="operator", password_hash=hash_password("dispatch123"), full_name="Officer Shawsti Singh", role="CONTROL_ROOM_OPERATOR", badge_number="GN-DSP-04", phone="+91 98100 00002"),
                User(username="utsav", password_hash=hash_password("utsav123"), full_name="Lead Architect Utsav", role="SUPER_ADMIN", badge_number="GN-ENG-07", phone="+91 98100 00003"),
                User(username="medic", password_hash=hash_password("medic123"), full_name="Paramedic Dr. Ananya Sen", role="AMBULANCE_DRIVER", badge_number="GN-MED-12", phone="+91 98100 00004", vehicle_id=1),
                User(username="aiims_admin", password_hash=hash_password("hospital123"), full_name="Dr. Verma (Trauma Chief)", role="HOSPITAL_OPERATOR", badge_number="GN-HSP-99", phone="+91 98100 00005", hospital_id=1),
            ]
            db.add_all(seed_users)
            db.commit()
            logger.info("Database initialized with seed users.")

        # 2. Seed Hospitals if empty
        if db.query(Hospital).count() == 0:
            seed_hospitals = [
                Hospital(id=1, name="AIIMS Apex Trauma Centre", category="Level-1 Apex Trauma Institute", address="Ring Road, Safdarjung Enclave, New Delhi", latitude=28.5672, longitude=77.2100, grid_node=67, total_icu_beds=24, available_icu_beds=6, total_general_beds=60, available_general_beds=18, trauma_bays=18, blood_bank_status="O-ve: 14 units, A+ve: 28 units, B+ve: 22 units", emergency_hotline="+91-11-2659-3200", status="Operational"),
                Hospital(id=2, name="Safdarjung Hospital Emergency Block", category="Level-1 Specialized Burns & Trauma Centre", address="Ring Road, opposite AIIMS, New Delhi", latitude=28.5701, longitude=77.2078, grid_node=71, total_icu_beds=30, available_icu_beds=8, total_general_beds=75, available_general_beds=22, trauma_bays=22, blood_bank_status="Full blood bank stock 24/7", emergency_hotline="+91-11-2616-5060", status="Operational"),
                Hospital(id=3, name="Dr. Ram Manohar Lohia (RML) Hospital", category="Level-2 Central Regional Emergency Hospital", address="Baba Kharak Singh Marg, Connaught Place, New Delhi", latitude=28.6245, longitude=77.1994, grid_node=15, total_icu_beds=18, available_icu_beds=4, total_general_beds=50, available_general_beds=12, trauma_bays=12, blood_bank_status="O-ve: 6 units, A+ve: 15 units", emergency_hotline="+91-11-2336-5525", status="Operational"),
                Hospital(id=4, name="Max Super Speciality Hospital Saket", category="Level-1 Advanced Cardiac & Neuro Trauma", address="1, 2 Press Enclave Marg, Saket, New Delhi", latitude=28.5282, longitude=77.2115, grid_node=88, total_icu_beds=20, available_icu_beds=7, total_general_beds=55, available_general_beds=14, trauma_bays=14, blood_bank_status="All major groups available", emergency_hotline="+91-11-2651-5050", status="Operational"),
            ]
            db.add_all(seed_hospitals)
            db.commit()
            logger.info("Database initialized with regional trauma hospitals.")

        # 3. Seed Vehicles if empty
        if db.query(Vehicle).count() == 0:
            seed_vehicles = [
                Vehicle(id=1, callsign="AMB-101", vehicle_type="ambulance", label="🚑 CATS Rapid Ambulance #101", station_base="Central Fire HQ (Connaught Place)", current_lat=28.6315, current_lon=77.2167, current_node=0, status="Available", crew_lead="Paramedic Rajesh Kumar", fuel_level_pct=95, active_driver_id=4),
                Vehicle(id=2, callsign="ALS-204", vehicle_type="advanced_life_support", label="🚑 Advanced Life Support Unit #204", station_base="AIIMS Rapid Deployment Depot", current_lat=28.5672, current_lon=77.2100, current_node=67, status="Available", crew_lead="Dr. Vikram Seth (ALS)", fuel_level_pct=88),
                Vehicle(id=3, callsign="FIRE-501", vehicle_type="fire_engine", label="🚒 Heavy Foam Tender #501", station_base="Connaught Place Fire Station", current_lat=28.6328, current_lon=77.2195, current_node=0, status="Available", crew_lead="Station Officer Manjit Singh", fuel_level_pct=100),
                Vehicle(id=4, callsign="PCR-09", vehicle_type="police_car", label="👮 Delhi Police Highway Patrol #09", station_base="Ring Road Intercept Post", current_lat=28.5701, current_lon=77.2345, current_node=53, status="Available", crew_lead="Sub-Inspector Sandeep Rao", fuel_level_pct=92),
                Vehicle(id=5, callsign="RESC-303", vehicle_type="rescue_van", label="🛠️ Heavy Rescue Hydraulic Unit #303", station_base="Pragati Maidan Emergency Base", current_lat=28.6180, current_lon=77.2410, current_node=12, status="Available", crew_lead="Lead Rescuer Amit Sharma", fuel_level_pct=85),
                Vehicle(id=6, callsign="HELI-01", vehicle_type="medical_helicopter", label="🚁 AIIMS Air Trauma Helicopter #01", station_base="Safdarjung Helipad Station", current_lat=28.5850, current_lon=77.2050, current_node=24, status="Available", crew_lead="Captain R. K. Nair", fuel_level_pct=100),
                Vehicle(id=7, callsign="MEDIC-07", vehicle_type="ambulance", label="🏍️ Rapid Two-Wheeler Medic #07", station_base="DND Expressway Plaza", current_lat=28.5833, current_lon=77.2833, current_node=84, status="Available", crew_lead="First Responder Tarun Joshi", fuel_level_pct=98),
            ]
            db.add_all(seed_vehicles)
            db.commit()
            logger.info("Database initialized with emergency fleet units.")

        # 4. Seed V2X Mesh Nodes if empty
        if db.query(V2XMeshNode).count() == 0:
            seed_nodes = [
                V2XMeshNode(node_id="RSU-01", node_type="RSU", label="NHAI Smart Gantry - Connaught Hub", lat=28.6315, lon=77.2167, tx_power_dbm=24.0, status="Online"),
                V2XMeshNode(node_id="AMB-101", node_type="Ambulance", label="CATS Ambulance V2X Transceiver", lat=28.6315, lon=77.2167, tx_power_dbm=20.0, status="Online"),
                V2XMeshNode(node_id="PCR-09", node_type="Police_Vehicle", label="Police Patrol Mobile Node", lat=28.5701, lon=77.2345, tx_power_dbm=20.0, status="Online"),
                V2XMeshNode(node_id="BUS-412", node_type="Transit_Bus", label="DTC Electric Bus Mesh Repeater", lat=28.6050, lon=77.2250, tx_power_dbm=18.0, status="Online"),
                V2XMeshNode(node_id="RSU-07", node_type="RSU", label="Ring Road Smart Microwave Sensor", lat=28.5700, lon=77.2200, tx_power_dbm=24.0, status="Online"),
                V2XMeshNode(node_id="RSU-14", node_type="RSU", label="AIIMS Flyover Emergency Beacon", lat=28.5670, lon=77.2100, tx_power_dbm=24.0, status="Online"),
            ]
            db.add_all(seed_nodes)
            db.commit()
            logger.info("Database initialized with V2X mesh nodes.")

        # 5. Seed initial realistic incidents if empty
        if db.query(Incident).count() == 0:
            seed_inc = Incident(
                incident_id="INC-20261124-1001",
                witness_name="Mohan Kumar (Eyewitness)",
                witness_phone="+91-98112-34567",
                witness_statement="Major explosion at the central fuel depot on Outer Ring Road! Three vehicles engulfed in flames, thick toxic black smoke, two casualties visible near the blast zone.",
                category="Fire/Explosion",
                severity="Critical",
                latitude=28.5680,
                longitude=77.2150,
                grid_node=67,
                landmark="AIIMS Flyover West Junction",
                status="Verified",
                urgency_index=9.50,
                golden_hour_sla_min=8.0,
                ai_analysis_reasoning="Critical fire and explosion indicators detected with 2 trapped casualties. Foam tender and ALS ambulance required.",
                vehicles_involved=3,
                casualties_count=2,
                hazards_detected=json.dumps(["Fire", "Smoke", "Toxic Fumes"]),
                recommended_units=json.dumps(["🚑 CATS Ambulance (ALS)", "🚒 Heavy Foam Tender", "👮 Delhi Police Patrol"]),
                reported_by="citizen_public",
            )
            db.add(seed_inc)
            db.commit()
            logger.info("Database initialized with seed incident.")

    except Exception as exc:
        db.rollback()
        logger.error(f"Error during startup database seed: {exc}")
    finally:
        db.close()
