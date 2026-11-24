"""
modules/database.py
===================
Enterprise-grade SQLite database layer for GuardianNodes RoadSoS.
Provides persistent storage, relational tables, transaction safety,
data validation, and automated seed data initialization.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("roadsafety.db")

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "roadsafety.db"
EVIDENCE_DIR = DB_DIR / "evidence"

DB_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db_connection():
    """Context manager for SQLite connections with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error(f"Database transaction rolled back due to error: {exc}")
        raise exc
    finally:
        conn.close()


def init_database() -> None:
    """Initialize all schema tables and seed master records if empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table (RBAC)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'dispatcher', 'hospital_operator', 'first_responder')),
            badge_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );
        """)

        # 2. Incidents Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            witness_name TEXT DEFAULT 'Anonymous Citizen',
            witness_phone TEXT DEFAULT 'N/A',
            witness_statement TEXT NOT NULL,
            sensor_payload TEXT,
            category TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            grid_node INTEGER NOT NULL,
            landmark TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Reported', 'AI Analyzed', 'Verified', 'Dispatched', 'En Route', 'On Scene', 'Resolved', 'Cancelled')),
            urgency_index REAL NOT NULL,
            golden_hour_sla_min REAL NOT NULL,
            ai_analysis_reasoning TEXT,
            extracted_entities TEXT,
            recommended_units TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reported_by_username TEXT DEFAULT 'system'
        );
        """)

        # 3. Incident Evidence Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            visual_tags TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
        );
        """)

        # 4. Emergency Vehicles Fleet Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            callsign TEXT UNIQUE NOT NULL,
            vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('ambulance', 'advanced_life_support', 'fire_engine', 'police_car', 'rescue_van', 'medical_helicopter')),
            label TEXT NOT NULL,
            station_base TEXT NOT NULL,
            current_lat REAL NOT NULL,
            current_lon REAL NOT NULL,
            current_node INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Available', 'Dispatched', 'En Route', 'On Scene', 'Busy', 'Maintenance')),
            crew_lead TEXT NOT NULL,
            fuel_level_pct INTEGER DEFAULT 100,
            active_incident_id TEXT,
            FOREIGN KEY (active_incident_id) REFERENCES incidents(incident_id) ON DELETE SET NULL
        );
        """)

        # 5. Dispatches Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatches (
            dispatch_id TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL,
            vehicle_id INTEGER NOT NULL,
            assigned_by TEXT NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            en_route_at TIMESTAMP,
            on_scene_at TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT NOT NULL CHECK(status IN ('Active', 'En Route', 'On Scene', 'Completed', 'Cancelled', 'Reassigned')),
            route_time_min REAL NOT NULL,
            route_path_nodes TEXT,
            dispatch_notes TEXT,
            FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE,
            FOREIGN KEY (vehicle_id) REFERENCES emergency_vehicles(id) ON DELETE RESTRICT
        );
        """)

        # 6. Regional Hospitals Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            address TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            grid_node INTEGER NOT NULL,
            total_icu_beds INTEGER NOT NULL,
            available_icu_beds INTEGER NOT NULL,
            trauma_bays INTEGER NOT NULL,
            blood_bank_status TEXT NOT NULL,
            emergency_hotline TEXT NOT NULL,
            status TEXT DEFAULT 'Operational' CHECK(status IN ('Operational', 'Surge Capacity', 'Diversion'))
        );
        """)

        # 7. Hospital Bed Reservations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospital_bed_reservations (
            reservation_id TEXT PRIMARY KEY,
            hospital_id INTEGER NOT NULL,
            incident_id TEXT NOT NULL,
            patient_identifier TEXT NOT NULL,
            bed_type TEXT NOT NULL,
            reserved_by TEXT NOT NULL,
            reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            patient_handover_status TEXT NOT NULL CHECK(patient_handover_status IN ('Pending Arrival', 'Patient Admitted', 'Transferred', 'Released')),
            handover_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE RESTRICT,
            FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
        );
        """)

        # 8. V2X Mesh Network Nodes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v2x_mesh_nodes (
            node_id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,
            label TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            firmware_version TEXT DEFAULT 'v2.5-ble',
            tx_power_dbm REAL DEFAULT 20.0,
            status TEXT DEFAULT 'Online' CHECK(status IN ('Online', 'Relaying', 'Degraded', 'Offline'))
        );
        """)

        # 9. V2X Relay Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v2x_relay_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_hops INTEGER NOT NULL,
            hops_completed INTEGER NOT NULL,
            delivery_ratio REAL NOT NULL,
            total_latency_ms REAL NOT NULL,
            raw_payload_hex TEXT NOT NULL,
            final_status TEXT NOT NULL,
            hop_details_json TEXT NOT NULL
        );
        """)

        # 10. Audit Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            action TEXT NOT NULL,
            target_entity TEXT,
            details TEXT,
            ip_address TEXT DEFAULT '127.0.0.1'
        );
        """)

        _seed_master_data(conn)


def _seed_master_data(conn: sqlite3.Connection) -> None:
    """Seed initial master data (users, hospitals, fleet, mesh nodes) if tables are empty."""
    cursor = conn.cursor()

    # 1. Seed Users (with hashed passwords)
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        import hashlib
        def h(pwd: str) -> str:
            # Salted SHA-256
            return hashlib.sha256(f"roadso_{pwd}_salt2026".encode()).hexdigest()

        seed_users = [
            ("admin", h("admin123"), "Commander Rohit Singh", "admin", "GN-CMD-01"),
            ("operator", h("dispatch123"), "Officer Shawsti Singh", "dispatcher", "GN-DSP-04"),
            ("utsav", h("utsav123"), "Senior Engineer Utsav", "admin", "GN-ENG-07"),
            ("medic", h("medic123"), "Paramedic Dr. Ananya Sen", "first_responder", "GN-MED-12"),
            ("aiims_admin", h("hospital123"), "Trauma Supervisor Dr. Verma", "hospital_operator", "GN-HSP-99"),
        ]
        cursor.executemany("""
        INSERT INTO users (username, password_hash, full_name, role, badge_number)
        VALUES (?, ?, ?, ?, ?);
        """, seed_users)

    # 2. Seed Hospitals
    cursor.execute("SELECT COUNT(*) FROM hospitals;")
    if cursor.fetchone()[0] == 0:
        seed_hospitals = [
            ("AIIMS Apex Trauma Centre", "Level-1 Apex Trauma Institute", "Ring Road, Safdarjung Enclave, New Delhi", 28.5672, 77.2100, 67, 24, 6, 18, "O-ve: 14 units, A+ve: 28 units, B+ve: 22 units", "+91-11-2659-3200 / 102", "Operational"),
            ("Safdarjung Hospital Emergency Block", "Level-1 Specialized Burns & Trauma Centre", "Ring Road, opposite AIIMS, New Delhi", 28.5701, 77.2078, 71, 30, 8, 22, "Full blood bank in stock 24/7", "+91-11-2616-5060 / 112", "Operational"),
            ("Dr. Ram Manohar Lohia (RML) Hospital", "Level-2 Central Regional Emergency Hospital", "Baba Kharak Singh Marg, Connaught Place, New Delhi", 28.6245, 77.1994, 15, 18, 4, 12, "O-ve: 6 units, A+ve: 15 units", "+91-11-2336-5525", "Operational"),
            ("Max Super Speciality Hospital Saket", "Level-1 Advanced Cardiac & Neuro Trauma", "1, 2 Press Enclave Marg, Saket, New Delhi", 28.5282, 77.2115, 88, 20, 7, 14, "All major blood groups available", "+91-11-2651-5050", "Operational"),
        ]
        cursor.executemany("""
        INSERT INTO hospitals (name, category, address, latitude, longitude, grid_node, total_icu_beds, available_icu_beds, trauma_bays, blood_bank_status, emergency_hotline, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, seed_hospitals)

    # 3. Seed Emergency Vehicles Fleet
    cursor.execute("SELECT COUNT(*) FROM emergency_vehicles;")
    if cursor.fetchone()[0] == 0:
        seed_vehicles = [
            ("AMB-101", "ambulance", "🚑 CATS Rapid Ambulance #101", "Central Fire HQ (Connaught Place)", 28.6315, 77.2167, 0, "Available", "Paramedic Rajesh Kumar", 95, None),
            ("ALS-204", "advanced_life_support", "🚑 Advanced Life Support Unit #204", "AIIMS Rapid Deployment Depot", 28.5672, 77.2100, 67, "Available", "Dr. Vikram Seth (ALS)", 88, None),
            ("FIRE-501", "fire_engine", "🚒 Heavy Foam Tender #501", "Connaught Place Fire Station", 28.6328, 77.2195, 0, "Available", "Station Officer Manjit Singh", 100, None),
            ("PCR-09", "police_car", "👮 Delhi Police Highway Patrol #09", "Ring Road Intercept Post", 28.5701, 77.2345, 53, "Available", "Sub-Inspector Sandeep Rao", 92, None),
            ("RESC-303", "rescue_van", "🛠️ Heavy Rescue Hydraulic Unit #303", "Pragati Maidan Emergency Base", 28.6180, 77.2410, 12, "Available", "Lead Rescuer Amit Sharma", 85, None),
            ("HELI-01", "medical_helicopter", "🚁 AIIMS Air Trauma Helicopter #01", "Safdarjung Helipad Station", 28.5850, 77.2050, 24, "Available", "Captain R. K. Nair", 100, None),
            ("MEDIC-07", "ambulance", "🏍️ Rapid Two-Wheeler Medic #07", "DND Expressway Plaza", 28.5833, 77.2833, 84, "Available", "First Responder Tarun Joshi", 98, None),
        ]
        cursor.executemany("""
        INSERT INTO emergency_vehicles (callsign, vehicle_type, label, station_base, current_lat, current_lon, current_node, status, crew_lead, fuel_level_pct, active_incident_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, seed_vehicles)

    # 4. Seed V2X Mesh Relay Nodes
    cursor.execute("SELECT COUNT(*) FROM v2x_mesh_nodes;")
    if cursor.fetchone()[0] == 0:
        seed_mesh = [
            ("RSU-01", "RSU", "NHAI Smart Gantry - Connaught Hub", 28.6315, 77.2167, "v2.5-rsu", 24.0, "Online"),
            ("AMB-101", "Ambulance", "CATS Ambulance V2X Transceiver", 28.6315, 77.2167, "v2.5-vanet", 20.0, "Online"),
            ("PCR-09", "Police_Vehicle", "Police Patrol Mobile Node", 28.5701, 77.2345, "v2.5-vanet", 20.0, "Online"),
            ("BUS-412", "Transit_Bus", "DTC Electric Bus Mesh Repeater", 28.6050, 77.2250, "v2.5-vanet", 18.0, "Online"),
            ("RSU-07", "RSU", "Ring Road Smart Microwave Sensor", 28.5700, 77.2200, "v2.5-rsu", 24.0, "Online"),
            ("RSU-14", "RSU", "AIIMS Flyover Emergency Beacon", 28.5670, 77.2100, "v2.5-rsu", 24.0, "Online"),
        ]
        cursor.executemany("""
        INSERT INTO v2x_mesh_nodes (node_id, node_type, label, lat, lon, firmware_version, tx_power_dbm, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, seed_mesh)

    # 5. Seed initial realistic incidents if empty
    cursor.execute("SELECT COUNT(*) FROM incidents;")
    if cursor.fetchone()[0] == 0:
        seed_incidents = [
            (
                "INC-20261124-1001",
                "Mohan Kumar (Eyewitness)",
                "+91-98112-34567",
                "Major explosion at the central fuel depot on Outer Ring Road! Three vehicles engulfed in flames, thick toxic black smoke, two casualties visible near the blast zone.",
                json.dumps({"source": "CCTV-RingRoad-Cam04", "flame_detected": True}),
                "Fire/Explosion",
                28.6140,
                77.2280,
                35,
                "Outer Ring Road / Pragati Corridor",
                "Dispatched",
                9.65,
                8.0,
                "Explosion keywords detected with active fire and casualties. Highest priority dispatch for fire tender and ALS ambulance.",
                json.dumps({"vehicle_count": ["3"], "casualty_count": ["2"], "fire_mention": ["fire", "explosion"]}),
                json.dumps(["🚒 Advanced Fire Engine", "🚑 Rapid ALS Paramedic", "👮 Police Traffic Escort"]),
                "admin",
            ),
            (
                "INC-20261124-1002",
                "Priya Sharma (Commuter)",
                "+91-98765-43210",
                "Multi-vehicle crash on NH-48 Airport Highway. Four passenger cars and one tempo collided. Three people seriously injured, one driver trapped in cabin.",
                json.dumps({"source": "Automatic Crash Notification (eCall)", "speed_delta_kph": 65}),
                "Critical Medical Trauma",
                28.5355,
                77.1025,
                95,
                "NH-48 Mahipalpur Expressway Terminal",
                "Verified",
                9.10,
                8.0,
                "High casualty count with passenger entrapment. Rapid extrication and Level-1 trauma handover required within Golden Hour window.",
                json.dumps({"vehicle_count": ["5"], "casualty_count": ["3"], "entrapment_mention": ["trapped"]}),
                json.dumps(["🚑 Advanced Life Support (ALS)", "🚒 Heavy Hydraulic Rescue (Jaws of Life)", "👮 Highway Patrol"]),
                "operator",
            ),
            (
                "INC-20261124-1003",
                "Vikram Malhotra",
                "+91-99887-76655",
                "Minor fender bender near shopping mall on Ring Road. Two compact cars touched bumpers, zero injuries reported, traffic moving slowly.",
                json.dumps({"source": "Citizen Mobile App", "airbag_status": "Not Deployed"}),
                "Minor Collision",
                28.5701,
                77.2345,
                53,
                "Ring Road - Moolchand Underpass",
                "Resolved",
                2.45,
                30.0,
                "Explicit statement of zero casualties and low impact. Local traffic patrol routed to clear lane.",
                json.dumps({"vehicle_count": ["2"], "casualty_count": ["0"]}),
                json.dumps(["👮 Local PCR Police Van"]),
                "operator",
            ),
        ]
        cursor.executemany("""
        INSERT INTO incidents (
            incident_id, witness_name, witness_phone, witness_statement, sensor_payload,
            category, latitude, longitude, grid_node, landmark, status, urgency_index,
            golden_hour_sla_min, ai_analysis_reasoning, extracted_entities, recommended_units, reported_by_username
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, seed_incidents)

        # Connect initial dispatch for INC-20261124-1001 with vehicle FIRE-501
        cursor.execute("SELECT id FROM emergency_vehicles WHERE callsign = 'FIRE-501';")
        veh_row = cursor.fetchone()
        if veh_row:
            veh_id = veh_row[0]
            cursor.execute("""
            INSERT INTO dispatches (dispatch_id, incident_id, vehicle_id, assigned_by, status, route_time_min, dispatch_notes)
            VALUES ('DSP-20261124-001', 'INC-20261124-1001', ?, 'admin', 'En Route', 7.4, 'Immediate foam deployment instructed');
            """, (veh_id,))
            cursor.execute("UPDATE emergency_vehicles SET status = 'En Route', active_incident_id = 'INC-20261124-1001' WHERE id = ?;", (veh_id,))


# Initialize database schema immediately on import
init_database()
