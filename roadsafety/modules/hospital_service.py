"""
modules/hospital_service.py
===========================
Hospital coordination, live ICU bed tracking, bed reservations,
negative capacity prevention, and patient handover tracking.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.database import get_db_connection
from modules.auth import log_audit_action

logger = logging.getLogger("roadsafety.hospital")


def get_all_hospitals() -> list[dict]:
    """Retrieve all regional trauma centers with live capacity."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT h.*,
               (SELECT COUNT(*) FROM hospital_bed_reservations r 
                WHERE r.hospital_id = h.id AND r.patient_handover_status = 'Pending Arrival') as pending_admissions
        FROM hospitals h
        ORDER BY h.category, h.name;
        """)
        return [dict(r) for r in cursor.fetchall()]


def get_hospital_by_id(hospital_id: int) -> Optional[dict]:
    """Retrieve hospital details by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hospitals WHERE id = ?;", (hospital_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def reserve_hospital_bed(
    hospital_id: int,
    incident_id: str,
    patient_identifier: str,
    bed_type: str,
    reserved_by: str,
    notes: str = "",
) -> str:
    """
    Transactionally reserve an emergency trauma/ICU bed.
    Prevents negative bed counts and records an active reservation.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Check hospital availability
        cursor.execute("""
        SELECT name, available_icu_beds, total_icu_beds, status
        FROM hospitals WHERE id = ?;
        """, (hospital_id,))
        hosp = cursor.fetchone()

        if not hosp:
            raise ValueError(f"Hospital ID {hospital_id} does not exist.")

        if hosp["status"] == "Diversion":
            raise ValueError(f"Cannot reserve bed at {hosp['name']}: Hospital is on total Diversion protocol.")

        if hosp["available_icu_beds"] <= 0:
            raise ValueError(
                f"Zero available ICU beds at {hosp['name']} (0/{hosp['total_icu_beds']}). Immediate diversion required!"
            )

        # 2. Check if this patient already has an active reservation
        cursor.execute("""
        SELECT reservation_id FROM hospital_bed_reservations
        WHERE hospital_id = ? AND incident_id = ? AND patient_identifier = ?
          AND patient_handover_status = 'Pending Arrival';
        """, (hospital_id, incident_id, patient_identifier))
        existing = cursor.fetchone()
        if existing:
            raise ValueError(f"Patient {patient_identifier} already has an active reservation ({existing['reservation_id']}).")

        # 3. Create reservation record
        res_id = f"RES-{datetime.now().strftime('%Y%m%d')}-{int(time.time() % 10000):04d}"
        cursor.execute("""
        INSERT INTO hospital_bed_reservations (
            reservation_id, hospital_id, incident_id, patient_identifier,
            bed_type, reserved_by, patient_handover_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, 'Pending Arrival', ?);
        """, (res_id, hospital_id, incident_id, patient_identifier, bed_type, reserved_by, notes))

        # 4. Safely decrement available bed count
        cursor.execute("""
        UPDATE hospitals
        SET available_icu_beds = available_icu_beds - 1
        WHERE id = ? AND available_icu_beds > 0;
        """, (hospital_id,))

        log_audit_action(
            username=reserved_by,
            role="operator",
            action="RESERVE_HOSPITAL_BED",
            target=res_id,
            details=f"Reserved {bed_type} at {hosp['name']} for incident {incident_id} (Patient: {patient_identifier}).",
            conn=conn,
        )

        return res_id


def update_patient_handover(
    reservation_id: str,
    new_status: str,
    username: str,
    notes: str = "",
) -> None:
    """
    Update patient handover lifecycle:
      - Pending Arrival -> Patient Admitted -> Transferred -> Released.
    If released or transferred, releases the reserved ICU bed back to capacity.
    """
    valid_statuses = ('Pending Arrival', 'Patient Admitted', 'Transferred', 'Released')
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid handover status: {new_status}")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT r.*, h.name as hospital_name
        FROM hospital_bed_reservations r
        JOIN hospitals h ON r.hospital_id = h.id
        WHERE r.reservation_id = ?;
        """, (reservation_id,))
        res = cursor.fetchone()

        if not res:
            raise ValueError(f"Reservation {reservation_id} not found.")

        old_status = res["patient_handover_status"]

        # Update reservation
        cursor.execute("""
        UPDATE hospital_bed_reservations
        SET patient_handover_status = ?,
            handover_at = CASE WHEN ? = 'Patient Admitted' THEN CURRENT_TIMESTAMP ELSE handover_at END,
            notes = CASE WHEN ? != '' THEN notes || ' [' || ? || ']' ELSE notes END
        WHERE reservation_id = ?;
        """, (new_status, new_status, notes, notes, reservation_id))

        # If patient is released or transferred away, return the bed to available pool
        if new_status in ('Released', 'Transferred') and old_status in ('Pending Arrival', 'Patient Admitted'):
            cursor.execute("""
            UPDATE hospitals
            SET available_icu_beds = MIN(total_icu_beds, available_icu_beds + 1)
            WHERE id = ?;
            """, (res["hospital_id"],))

        log_audit_action(
            username=username,
            role="hospital_operator",
            action="UPDATE_PATIENT_HANDOVER",
            target=reservation_id,
            details=f"Handover updated from {old_status} to {new_status} at {res['hospital_name']}.",
            conn=conn,
        )


def get_active_reservations(limit: int = 50) -> list[dict]:
    """Retrieve hospital bed reservations with hospital and incident metadata."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT r.*, h.name as hospital_name, h.category as hospital_category,
               i.category as incident_category, i.landmark as incident_landmark, i.urgency_index
        FROM hospital_bed_reservations r
        JOIN hospitals h ON r.hospital_id = h.id
        JOIN incidents i ON r.incident_id = i.incident_id
        ORDER BY r.reserved_at DESC LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
