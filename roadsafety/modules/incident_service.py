"""
modules/incident_service.py
===========================
Incident reporting, AI-driven severity triage, evidence storage,
status lifecycle management, search, and analytics queries.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.database import get_db_connection, EVIDENCE_DIR
from modules.auth import log_audit_action
from modules.triage_engine import IntelligentTriageEngine
from modules.routing_engine import GraphRoutingEngine

logger = logging.getLogger("roadsafety.incident")

_triage_engine = IntelligentTriageEngine()
_routing_engine = GraphRoutingEngine(seed=42)


def generate_incident_id(cursor=None) -> str:
    """Generate a collision-free sequential/randomized incident ID with uniqueness check."""
    today = datetime.now().strftime('%Y%m%d')
    for _ in range(20):
        rand_code = secrets.randbelow(90000) + 10000
        candidate = f"INC-{today}-{rand_code}"
        if cursor is not None:
            cursor.execute("SELECT 1 FROM incidents WHERE incident_id = ?", (candidate,))
            if not cursor.fetchone():
                return candidate
        else:
            return candidate
    return f"INC-{today}-{uuid.uuid4().hex[:6].upper()}"


def create_incident(
    witness_statement: str,
    latitude: float,
    longitude: float,
    witness_name: str = "Anonymous Citizen",
    witness_phone: str = "N/A",
    sensor_payload: Optional[dict] = None,
    category_override: Optional[str] = None,
    visual_tags: Optional[list[str]] = None,
    evidence_files: Optional[list[Tuple[str, bytes]]] = None,
    username: str = "system",
) -> dict:
    """
    Process, analyze, and persist a new emergency road incident.
    Integrates AI zero-shot analysis, entity extraction, explainable reasoning,
    grid node snapping, and evidence storage.
    """
    if not witness_statement or not witness_statement.strip():
        raise ValueError("Incident report requires a non-empty statement or sensor description.")

    # 1. AI Analysis & Triage
    triage_result = _triage_engine.analyze(
        witness_text=witness_statement,
        visual_tags=visual_tags,
    )

    category = category_override if category_override else triage_result.top_label
    urgency_index = triage_result.urgency_index
    golden_hour_sla = triage_result.golden_hour_sla_min
    entities_json = json.dumps(triage_result.entities)
    recommended_units_json = json.dumps(triage_result.recommended_units)

    # 2. Generate Explainable AI Reasoning Text
    reasoning_parts = [
        f"AI classified this incident as '{category}' with Urgency Index {urgency_index:.2f}/10.00 ({triage_result.severity_level}).",
    ]
    if "casualty_count" in triage_result.entities:
        c_count = triage_result.entities["casualty_count"][0]
        if c_count == "0":
            reasoning_parts.append("Report explicitly confirmed zero casualties, suppressing critical medical penalties.")
        else:
            reasoning_parts.append(f"Identified {c_count} casualty/injuries requiring urgent trauma care.")
    if "vehicle_count" in triage_result.entities:
        reasoning_parts.append(f"Extracted {triage_result.entities['vehicle_count'][0]} vehicle(s) involved in collision.")
    if "fire_mention" in triage_result.entities:
        reasoning_parts.append("Flammable/fire explosion indicators detected; foam tender requested.")
    if "entrapment_mention" in triage_result.entities:
        reasoning_parts.append("Passenger entrapment keywords detected; heavy hydraulic extrication recommended.")
    if visual_tags:
        reasoning_parts.append(f"Multi-modal evidence flags added: {', '.join(visual_tags)}.")

    reasoning_text = " ".join(reasoning_parts)

    # 3. GPS Snapping to Municipal Road Grid
    snapped_node = _routing_engine.find_nearest_node(latitude, longitude)
    landmark = _routing_engine.get_node_label(snapped_node)

    # 4. Save to Database
    with get_db_connection() as conn:
        cursor = conn.cursor()
        incident_id = generate_incident_id(cursor)
        sensor_json = json.dumps(sensor_payload) if sensor_payload else "{}"
        cursor.execute("""
        INSERT INTO incidents (
            incident_id, witness_name, witness_phone, witness_statement,
            sensor_payload, category, latitude, longitude, grid_node, landmark,
            status, urgency_index, golden_hour_sla_min, ai_analysis_reasoning,
            extracted_entities, recommended_units, reported_by_username
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AI Analyzed', ?, ?, ?, ?, ?, ?);
        """, (
            incident_id, witness_name, witness_phone, witness_statement,
            sensor_json, category, latitude, longitude, snapped_node, landmark,
            urgency_index, golden_hour_sla, reasoning_text,
            entities_json, recommended_units_json, username,
        ))

        # 5. Save Evidence Files if provided
        if evidence_files:
            for fname, fbytes in evidence_files:
                safe_name = f"{incident_id}_{int(time.time())}_{fname}"
                dest_path = EVIDENCE_DIR / safe_name
                with open(dest_path, "wb") as f_out:
                    f_out.write(fbytes)

                cursor.execute("""
                INSERT INTO incident_evidence (incident_id, evidence_type, file_name, file_path, visual_tags)
                VALUES (?, 'photo', ?, ?, ?);
                """, (incident_id, safe_name, str(dest_path), json.dumps(visual_tags or [])))

        log_audit_action(
            username=username,
            role="operator",
            action="CREATE_INCIDENT",
            target=incident_id,
            details=f"New incident logged at {landmark}. Urgency: {urgency_index:.2f}. Category: {category}.",
            conn=conn,
        )

    return get_incident_by_id(incident_id)


def get_all_incidents(
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Retrieve filtered incident records from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM incidents WHERE 1=1"
        params: list[Any] = []

        if status_filter and status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)

        if category_filter and category_filter != "All":
            query += " AND category = ?"
            params.append(category_filter)

        if search_query and search_query.strip():
            query += " AND (incident_id LIKE ? OR witness_statement LIKE ? OR landmark LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        cursor.execute(query, params)
        incidents = [dict(r) for r in cursor.fetchall()]

        # Parse JSON fields
        for inc in incidents:
            try:
                inc["entities_dict"] = json.loads(inc["extracted_entities"] or "{}")
            except Exception:
                inc["entities_dict"] = {}
            try:
                inc["units_list"] = json.loads(inc["recommended_units"] or "[]")
            except Exception:
                inc["units_list"] = []

        return incidents


def get_incident_by_id(incident_id: str) -> Optional[dict]:
    """Retrieve complete incident details including dispatches and evidence."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE incident_id = ?;", (incident_id,))
        row = cursor.fetchone()
        if not row:
            return None

        inc = dict(row)
        try:
            inc["entities_dict"] = json.loads(inc["extracted_entities"] or "{}")
        except Exception:
            inc["entities_dict"] = {}
        try:
            inc["units_list"] = json.loads(inc["recommended_units"] or "[]")
        except Exception:
            inc["units_list"] = []

        # Get evidence
        cursor.execute("SELECT * FROM incident_evidence WHERE incident_id = ?;", (incident_id,))
        inc["evidence"] = [dict(e) for e in cursor.fetchall()]

        # Get dispatches
        cursor.execute("""
        SELECT d.*, v.callsign, v.label as vehicle_label, v.vehicle_type, v.crew_lead
        FROM dispatches d
        JOIN emergency_vehicles v ON d.vehicle_id = v.id
        WHERE d.incident_id = ?
        ORDER BY d.assigned_at DESC;
        """, (incident_id,))
        inc["dispatches"] = [dict(d) for d in cursor.fetchall()]

        # Get reservations
        cursor.execute("""
        SELECT r.*, h.name as hospital_name
        FROM hospital_bed_reservations r
        JOIN hospitals h ON r.hospital_id = h.id
        WHERE r.incident_id = ?
        ORDER BY r.reserved_at DESC;
        """, (incident_id,))
        inc["bed_reservations"] = [dict(r) for r in cursor.fetchall()]

        return inc


def update_incident_status(incident_id: str, new_status: str, username: str) -> None:
    """Transition incident status with validation and release vehicles if resolved."""
    valid_statuses = ('Reported', 'AI Analyzed', 'Verified', 'Dispatched', 'En Route', 'On Scene', 'Resolved', 'Cancelled')
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid incident status '{new_status}'.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM incidents WHERE incident_id = ?;", (incident_id,))
        inc = cursor.fetchone()
        if not inc:
            raise ValueError(f"Incident {incident_id} not found.")

        old_status = inc["status"]
        cursor.execute("""
        UPDATE incidents SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE incident_id = ?;
        """, (new_status, incident_id))

        # If incident resolved or cancelled, release any assigned active vehicles
        if new_status in ('Resolved', 'Cancelled'):
            cursor.execute("""
            UPDATE emergency_vehicles
            SET status = 'Available', active_incident_id = NULL
            WHERE active_incident_id = ?;
            """, (incident_id,))

            cursor.execute("""
            UPDATE dispatches
            SET status = CASE WHEN ? = 'Resolved' THEN 'Completed' ELSE 'Cancelled' END,
                completed_at = CURRENT_TIMESTAMP
            WHERE incident_id = ? AND status IN ('Active', 'En Route', 'On Scene');
            """, (new_status, incident_id))

        log_audit_action(
            username=username,
            role="operator",
            action="UPDATE_INCIDENT_STATUS",
            target=incident_id,
            details=f"Status transitioned from '{old_status}' to '{new_status}'.",
            conn=conn,
        )


def get_incident_kpis() -> dict:
    """Compute real-time operational KPIs from persistent database records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM incidents;")
        total_incidents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status NOT IN ('Resolved', 'Cancelled');")
        active_incidents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Resolved';")
        resolved_incidents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM emergency_vehicles WHERE status = 'Available';")
        available_vehicles = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM emergency_vehicles WHERE status IN ('Dispatched', 'En Route', 'On Scene');")
        dispatched_vehicles = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(available_icu_beds) FROM hospitals;")
        available_icu_beds = cursor.fetchone()[0] or 0

        cursor.execute("SELECT AVG(route_time_min) FROM dispatches WHERE status != 'Cancelled';")
        avg_response_time = cursor.fetchone()[0] or 0.0

        return {
            "total_incidents": total_incidents,
            "active_incidents": active_incidents,
            "resolved_incidents": resolved_incidents,
            "available_vehicles": available_vehicles,
            "dispatched_vehicles": dispatched_vehicles,
            "available_icu_beds": int(available_icu_beds),
            "avg_response_time": round(float(avg_response_time), 1),
        }
