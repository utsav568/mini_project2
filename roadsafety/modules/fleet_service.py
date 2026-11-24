"""
modules/fleet_service.py
========================
Vehicle fleet management, automated nearest-vehicle selection,
dispatch lifecycle tracking, and duplicate dispatch prevention.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.database import get_db_connection
from modules.auth import log_audit_action

logger = logging.getLogger("roadsafety.fleet")


def get_all_vehicles() -> list[dict]:
    """Retrieve full emergency vehicle fleet with live operational status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT v.*, i.landmark as active_landmark, i.category as active_category
        FROM emergency_vehicles v
        LEFT JOIN incidents i ON v.active_incident_id = i.incident_id
        ORDER BY v.vehicle_type, v.callsign;
        """)
        return [dict(r) for r in cursor.fetchall()]


def get_available_vehicles(vehicle_type: Optional[str] = None) -> list[dict]:
    """Return all vehicles currently in 'Available' state."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if vehicle_type:
            cursor.execute("""
            SELECT * FROM emergency_vehicles
            WHERE status = 'Available' AND vehicle_type = ?
            ORDER BY callsign;
            """, (vehicle_type,))
        else:
            cursor.execute("""
            SELECT * FROM emergency_vehicles
            WHERE status = 'Available'
            ORDER BY vehicle_type, callsign;
            """)
        return [dict(r) for r in cursor.fetchall()]


def dispatch_vehicle(
    incident_id: str,
    vehicle_id: int,
    assigned_by: str,
    route_time_min: float,
    route_path_nodes: Optional[list[int]] = None,
    dispatch_notes: str = "",
) -> str:
    """
    Transactionally dispatch a vehicle to an active incident.
    Guarantees no vehicle can be assigned to multiple active incidents simultaneously.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Verify vehicle availability under lock
        cursor.execute("SELECT callsign, label, status FROM emergency_vehicles WHERE id = ?;", (vehicle_id,))
        veh = cursor.fetchone()
        if not veh:
            raise ValueError(f"Vehicle ID {vehicle_id} does not exist.")

        if veh["status"] != "Available":
            raise ValueError(
                f"Cannot dispatch {veh['label']} ({veh['callsign']}): Vehicle is currently '{veh['status']}'."
            )

        # 2. Verify incident exists and is not already resolved/cancelled
        cursor.execute("SELECT status, category FROM incidents WHERE incident_id = ?;", (incident_id,))
        inc = cursor.fetchone()
        if not inc:
            raise ValueError(f"Incident {incident_id} not found.")

        if inc["status"] in ("Resolved", "Cancelled"):
            raise ValueError(f"Cannot dispatch to incident {incident_id} as its status is '{inc['status']}'.")

        # 3. Create dispatch record
        dispatch_id = f"DSP-{datetime.now().strftime('%Y%m%d')}-{int(time.time() % 10000):04d}"
        path_json = json.dumps(route_path_nodes or [])

        cursor.execute("""
        INSERT INTO dispatches (
            dispatch_id, incident_id, vehicle_id, assigned_by, status,
            route_time_min, route_path_nodes, dispatch_notes, en_route_at
        ) VALUES (?, ?, ?, ?, 'En Route', ?, ?, ?, CURRENT_TIMESTAMP);
        """, (dispatch_id, incident_id, vehicle_id, assigned_by, route_time_min, path_json, dispatch_notes))

        # 4. Update vehicle status and associate with incident
        cursor.execute("""
        UPDATE emergency_vehicles
        SET status = 'En Route', active_incident_id = ?
        WHERE id = ?;
        """, (incident_id, vehicle_id))

        # 5. Update incident status to 'Dispatched'
        cursor.execute("""
        UPDATE incidents
        SET status = 'Dispatched', updated_at = CURRENT_TIMESTAMP
        WHERE incident_id = ?;
        """, (incident_id,))

        log_audit_action(
            username=assigned_by,
            role="dispatcher",
            action="DISPATCH_VEHICLE",
            target=dispatch_id,
            details=f"Dispatched {veh['callsign']} to incident {incident_id}. ETA: {route_time_min:.1f} min.",
            conn=conn,
        )

        return dispatch_id


def update_vehicle_status(vehicle_id: int, new_status: str, username: str) -> None:
    """Update vehicle operational status (e.g. On Scene, Available, Maintenance)."""
    valid_statuses = ('Available', 'Dispatched', 'En Route', 'On Scene', 'Busy', 'Maintenance')
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid vehicle status: {new_status}")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT callsign, active_incident_id, status FROM emergency_vehicles WHERE id = ?;", (vehicle_id,))
        veh = cursor.fetchone()
        if not veh:
            raise ValueError(f"Vehicle ID {vehicle_id} not found.")

        # If marking available or maintenance, clear active incident association
        if new_status in ('Available', 'Maintenance'):
            cursor.execute("""
            UPDATE emergency_vehicles
            SET status = ?, active_incident_id = NULL
            WHERE id = ?;
            """, (new_status, vehicle_id))

            # If there was an active dispatch for this vehicle, complete it
            if veh["active_incident_id"]:
                cursor.execute("""
                UPDATE dispatches
                SET status = 'Completed', completed_at = CURRENT_TIMESTAMP
                WHERE vehicle_id = ? AND incident_id = ? AND status IN ('Active', 'En Route', 'On Scene');
                """, (vehicle_id, veh["active_incident_id"]))
        else:
            cursor.execute("""
            UPDATE emergency_vehicles SET status = ? WHERE id = ?;
            """, (new_status, vehicle_id))

        log_audit_action(
            username=username,
            role="operator",
            action="UPDATE_VEHICLE_STATUS",
            target=veh["callsign"],
            details=f"Status changed from {veh['status']} to {new_status}.",
            conn=conn,
        )


def cancel_dispatch(dispatch_id: str, username: str, reason: str = "") -> None:
    """Cancel an active dispatch and release the assigned emergency vehicle."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT d.*, v.callsign
        FROM dispatches d
        JOIN emergency_vehicles v ON d.vehicle_id = v.id
        WHERE d.dispatch_id = ?;
        """, (dispatch_id,))
        disp = cursor.fetchone()

        if not disp:
            raise ValueError(f"Dispatch {dispatch_id} not found.")

        # Release vehicle back to Available
        cursor.execute("""
        UPDATE emergency_vehicles
        SET status = 'Available', active_incident_id = NULL
        WHERE id = ?;
        """, (disp["vehicle_id"],))

        # Mark dispatch cancelled
        cursor.execute("""
        UPDATE dispatches
        SET status = 'Cancelled', dispatch_notes = dispatch_notes || ' [Cancelled: ' || ? || ']'
        WHERE dispatch_id = ?;
        """, (reason or "Operator cancelled", dispatch_id))

        # Check if incident has other active dispatches
        cursor.execute("""
        SELECT COUNT(*) FROM dispatches
        WHERE incident_id = ? AND status IN ('Active', 'En Route', 'On Scene');
        """, (disp["incident_id"],))
        remaining = cursor.fetchone()[0]

        if remaining == 0:
            cursor.execute("""
            UPDATE incidents SET status = 'Verified', updated_at = CURRENT_TIMESTAMP
            WHERE incident_id = ?;
            """, (disp["incident_id"],))

        log_audit_action(
            username=username,
            role="dispatcher",
            action="CANCEL_DISPATCH",
            target=dispatch_id,
            details=f"Cancelled dispatch for {disp['callsign']} on incident {disp['incident_id']}. Reason: {reason}",
            conn=conn,
        )


def get_dispatch_history(limit: int = 50) -> list[dict]:
    """Retrieve joined dispatch records for audit and analytics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT d.*, v.callsign, v.label as vehicle_label, v.vehicle_type,
               i.category as incident_category, i.landmark as incident_landmark, i.urgency_index
        FROM dispatches d
        JOIN emergency_vehicles v ON d.vehicle_id = v.id
        JOIN incidents i ON d.incident_id = i.incident_id
        ORDER BY d.assigned_at DESC LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
