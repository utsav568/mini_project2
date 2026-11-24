"""
roadsafety/backend/migrate_db.py
================================
Seamless schema migration helper: adds any missing columns to existing SQLite tables
preserving 100% of historical data, then creates new tables.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "roadsafety.db"


def run_migrations():
    if not DB_PATH.exists():
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    def get_columns(table_name: str) -> set:
        cursor.execute(f"PRAGMA table_info({table_name});")
        return {row[1] for row in cursor.fetchall()}

    tables = {row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}

    # 1. users
    if "users" in tables:
        cols = get_columns("users")
        if "phone" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT;")
        if "hospital_id" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN hospital_id INTEGER;")
        if "vehicle_id" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN vehicle_id INTEGER;")

    # 2. incidents
    if "incidents" in tables:
        cols = get_columns("incidents")
        if "severity" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN severity TEXT DEFAULT 'Moderate';")
        if "vehicles_involved" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN vehicles_involved INTEGER DEFAULT 1;")
        if "casualties_count" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN casualties_count INTEGER DEFAULT 0;")
        if "hazards_detected" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN hazards_detected TEXT DEFAULT '[]';")
        if "reported_by" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN reported_by TEXT DEFAULT 'citizen';")
        if "verified_by" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN verified_by TEXT;")
        if "verification_reason" not in cols:
            cursor.execute("ALTER TABLE incidents ADD COLUMN verification_reason TEXT;")

    # 3. emergency_vehicles
    if "emergency_vehicles" in tables:
        cols = get_columns("emergency_vehicles")
        if "active_driver_id" not in cols:
            cursor.execute("ALTER TABLE emergency_vehicles ADD COLUMN active_driver_id INTEGER;")
        if "updated_at" not in cols:
            cursor.execute("ALTER TABLE emergency_vehicles ADD COLUMN updated_at TIMESTAMP;")

    # 4. dispatches
    if "dispatches" in tables:
        cols = get_columns("dispatches")
        if "driver_id" not in cols:
            cursor.execute("ALTER TABLE dispatches ADD COLUMN driver_id INTEGER;")
        if "route_distance_km" not in cols:
            cursor.execute("ALTER TABLE dispatches ADD COLUMN route_distance_km REAL DEFAULT 5.0;")
        if "destination_hospital_id" not in cols:
            cursor.execute("ALTER TABLE dispatches ADD COLUMN destination_hospital_id INTEGER;")
        if "eta_min" not in cols:
            cursor.execute("ALTER TABLE dispatches ADD COLUMN eta_min REAL DEFAULT 10.0;")
        if "rejection_reason" not in cols:
            cursor.execute("ALTER TABLE dispatches ADD COLUMN rejection_reason TEXT;")
        if "at_hospital_at" not in cols:
            cursor.execute("ALTER TABLE dispatches ADD COLUMN at_hospital_at TIMESTAMP;")

    # 5. hospitals
    if "hospitals" in tables:
        cols = get_columns("hospitals")
        if "total_general_beds" not in cols:
            cursor.execute("ALTER TABLE hospitals ADD COLUMN total_general_beds INTEGER DEFAULT 50;")
        if "available_general_beds" not in cols:
            cursor.execute("ALTER TABLE hospitals ADD COLUMN available_general_beds INTEGER DEFAULT 15;")
        if "updated_at" not in cols:
            cursor.execute("ALTER TABLE hospitals ADD COLUMN updated_at TIMESTAMP;")

    # 6. hospital_bed_reservations
    if "hospital_bed_reservations" in tables:
        cols = get_columns("hospital_bed_reservations")
        if "dispatch_id" not in cols:
            cursor.execute("ALTER TABLE hospital_bed_reservations ADD COLUMN dispatch_id TEXT;")
        if "status" not in cols:
            cursor.execute("ALTER TABLE hospital_bed_reservations ADD COLUMN status TEXT DEFAULT 'Pending';")
        if "rejection_reason" not in cols:
            cursor.execute("ALTER TABLE hospital_bed_reservations ADD COLUMN rejection_reason TEXT;")

    conn.commit()
    conn.close()
    print("Database columns successfully migrated.")

if __name__ == "__main__":
    run_migrations()
