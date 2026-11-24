"""
modules/auth.py
===============
Security, Authentication, Role-Based Access Control (RBAC),
and Audit Logging for GuardianNodes RoadSoS.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.database import get_db_connection

logger = logging.getLogger("roadsafety.auth")

SECRET_SALT = "roadso_salt_2026_delhi_cad"

# RBAC Permissions Matrix
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "dispatch_vehicle",
        "cancel_dispatch",
        "reassign_vehicle",
        "create_incident",
        "modify_incident",
        "reserve_hospital_bed",
        "update_bed_status",
        "patient_handover",
        "manage_fleet",
        "manage_users",
        "view_analytics",
        "export_data",
        "configure_system",
    },
    "dispatcher": {
        "dispatch_vehicle",
        "cancel_dispatch",
        "reassign_vehicle",
        "create_incident",
        "modify_incident",
        "reserve_hospital_bed",
        "view_analytics",
        "export_data",
    },
    "hospital_operator": {
        "reserve_hospital_bed",
        "update_bed_status",
        "patient_handover",
        "view_incidents",
    },
    "first_responder": {
        "update_vehicle_status",
        "update_incident_status",
        "view_dispatches",
        "view_incidents",
    },
}


def hash_password(password: str) -> str:
    """Create a secure SHA-256 hash using HMAC and server salt."""
    return hmac.new(SECRET_SALT.encode(), password.encode(), hashlib.sha256).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Compare password hash securely against constant-time timing attacks."""
    # Also support seed data salted format for backward compatibility
    legacy_hash = hashlib.sha256(f"roadso_{password}_salt2026".encode()).hexdigest()
    if hmac.compare_digest(stored_hash, legacy_hash):
        return True
    current_hash = hash_password(password)
    return hmac.compare_digest(stored_hash, current_hash)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Verify user credentials against database and return user dictionary."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, username, password_hash, full_name, role, badge_number, is_active
        FROM users WHERE username = ?;
        """, (username.strip(),))
        row = cursor.fetchone()

        if not row:
            logger.warning(f"Failed login attempt: username '{username}' not found.")
            return None

        if not row["is_active"]:
            logger.warning(f"Deactivated user '{username}' attempted login.")
            return None

        if verify_password(password, row["password_hash"]):
            user_data = {
                "id": row["id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "role": row["role"],
                "badge_number": row["badge_number"],
            }
            log_audit_action(
                username=row["username"],
                role=row["role"],
                action="LOGIN_SUCCESS",
                target="AUTH",
                details=f"User {row['username']} logged in successfully.",
            )
            return user_data
        else:
            logger.warning(f"Failed login attempt: invalid password for '{username}'.")
            log_audit_action(
                username=username,
                role="unknown",
                action="LOGIN_FAILURE",
                target="AUTH",
                details=f"Invalid password for {username}.",
            )
            return None


def has_permission(role: str, action: str) -> bool:
    """Check if given role possesses permission to execute action."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return action in perms


def log_audit_action(
    username: str,
    role: str,
    action: str,
    target: str = "SYSTEM",
    details: str = "",
    ip_address: str = "127.0.0.1",
    conn: Optional[Any] = None,
) -> None:
    """Write an immutable entry to the audit_logs table."""
    try:
        if conn is not None:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_logs (username, role, action, target_entity, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (username, role, action, target, details, ip_address))
        else:
            with get_db_connection() as new_conn:
                cursor = new_conn.cursor()
                cursor.execute("""
                INSERT INTO audit_logs (username, role, action, target_entity, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (username, role, action, target, details, ip_address))
    except Exception as exc:
        logger.error(f"Failed to record audit log: {exc}")


def get_all_users() -> list[dict]:
    """Return all system users for administration."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, badge_number, is_active, created_at FROM users ORDER BY id;")
        return [dict(r) for r in cursor.fetchall()]


def get_recent_audit_logs(limit: int = 50) -> list[dict]:
    """Retrieve the most recent audit events."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, timestamp, username, role, action, target_entity, details, ip_address
        FROM audit_logs ORDER BY id DESC LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
