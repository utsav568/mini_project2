"""
roadsafety/backend/routers/incidents.py
=======================================
Incident intake, AI triage integration, verification, lifecycle tracking,
and evidence attachment endpoints.
"""

import os
import json
import secrets
import time
import uuid
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from ..database import get_db, BASE_DIR
from ..models import Incident, IncidentEvidence, AIAnalysis, IncidentHistory, Vehicle, Dispatch
from ..schemas import IncidentPublicCreate, IncidentResponse, IncidentVerifyRequest, IncidentUpdateStatus
from ..security import get_current_user_optional, get_current_user, require_roles, record_audit
from ..websocket_manager import ws_manager

# Re-use existing AI and Routing engines
import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.triage_engine import IntelligentTriageEngine
from modules.routing_engine import GraphRoutingEngine

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

_triage_engine = IntelligentTriageEngine()
_routing_engine = GraphRoutingEngine(seed=42)

EVIDENCE_DIR = BASE_DIR / "data" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def generate_incident_id(db: Optional[Session] = None) -> str:
    today = datetime.utcnow().strftime('%Y%m%d')
    for _ in range(20):
        rand_code = secrets.randbelow(90000) + 10000
        candidate = f"INC-{today}-{rand_code}"
        if db is not None:
            if not db.query(Incident).filter(Incident.incident_id == candidate).first():
                return candidate
        else:
            return candidate
    return f"INC-{today}-{uuid.uuid4().hex[:6].upper()}"


@router.post("", response_model=IncidentResponse)
async def report_incident(
    payload: IncidentPublicCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    """
    Public emergency reporting endpoint.
    Performs on-device AI classification, entity extraction, GPS road-snapping,
    database persistence, and live WebSocket broadcast to Control Room.
    """
    if not payload.witness_statement or not payload.witness_statement.strip():
        raise HTTPException(status_code=400, detail="Accident statement cannot be empty")

    # 1. AI Triage Analysis
    triage = _triage_engine.analyze(
        witness_text=payload.witness_statement,
        visual_tags=payload.visual_tags,
    )

    category = payload.category or triage.top_label
    urgency_index = triage.urgency_index
    golden_hour_sla = triage.golden_hour_sla_min
    severity = triage.severity_level

    # Extract entities
    veh_count = payload.vehicles_count or 1
    cas_count = payload.reported_casualties or 0
    if "vehicle_count" in triage.entities and veh_count == 1:
        try:
            veh_count = int(triage.entities["vehicle_count"][0])
        except Exception:
            pass
    if "casualty_count" in triage.entities and cas_count == 0:
        try:
            cas_count = int(triage.entities["casualty_count"][0])
        except Exception:
            pass

    # 2. GPS Snapping to Municipal Grid
    snapped_node = _routing_engine.find_nearest_node(payload.latitude, payload.longitude)
    landmark = _routing_engine.get_node_label(snapped_node)

    inc_id = generate_incident_id(db)
    reasoning = (
        f"AI classified as '{category}' with Urgency Index {urgency_index:.2f}/10.00 ({severity}). "
        f"Detected {veh_count} vehicles and {cas_count} casualties. "
        f"Recommended units: {', '.join(triage.recommended_units)}."
    )

    # 3. Create Incident Record
    username = user.username if user else "citizen_public"
    incident = Incident(
        incident_id=inc_id,
        witness_name=payload.witness_name or "Anonymous Citizen",
        witness_phone=payload.witness_phone or "N/A",
        witness_statement=payload.witness_statement,
        category=category,
        severity=severity,
        latitude=payload.latitude,
        longitude=payload.longitude,
        grid_node=snapped_node,
        landmark=landmark,
        status="Reported",
        urgency_index=urgency_index,
        golden_hour_sla_min=golden_hour_sla,
        ai_analysis_reasoning=reasoning,
        extracted_entities=json.dumps(triage.entities),
        recommended_units=json.dumps(triage.recommended_units),
        vehicles_involved=veh_count,
        casualties_count=cas_count,
        hazards_detected=json.dumps(payload.hazards or []),
        reported_by=username,
    )
    db.add(incident)

    # 4. Create AI Analysis Record
    ai_record = AIAnalysis(
        incident_id=inc_id,
        category=category,
        vehicle_count=veh_count,
        reported_casualties=cas_count,
        fire_mentioned="Fire/Explosion" in category or "fire" in payload.witness_statement.lower(),
        hazard_level="High" if urgency_index >= 7.0 else "Moderate",
        severity=severity,
        recommended_resources=json.dumps(triage.recommended_units),
        explanation=reasoning,
        confidence_score=0.88,
    )
    db.add(ai_record)

    # 5. History Record
    history = IncidentHistory(
        incident_id=inc_id,
        status_from=None,
        status_to="Reported",
        changed_by=username,
        notes="Incident reported via Public Citizen Portal",
    )
    db.add(history)
    db.commit()
    db.refresh(incident)

    # 6. WebSocket Broadcast to Control Room & Dashboards
    await ws_manager.broadcast("INCIDENT_REPORTED", {
        "incident_id": incident.incident_id,
        "category": incident.category,
        "severity": incident.severity,
        "landmark": incident.landmark,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "urgency_index": incident.urgency_index,
        "status": incident.status,
        "created_at": incident.created_at.isoformat(),
    })

    return incident


@router.get("", response_model=List[IncidentResponse])
def get_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List incidents with optional filtering by status, category, or search term."""
    query = db.query(Incident)
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    if category_filter:
        query = query.filter(Incident.category == category_filter)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Incident.incident_id.ilike(s)) |
            (Incident.witness_statement.ilike(s)) |
            (Incident.landmark.ilike(s))
        )
    return query.order_by(Incident.created_at.desc()).limit(limit).all()


@router.get("/{incident_id}")
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    """Retrieve full incident details including AI analysis, evidence, and dispatches."""
    inc = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    evidence = db.query(IncidentEvidence).filter(IncidentEvidence.incident_id == incident_id).all()
    ai_record = db.query(AIAnalysis).filter(AIAnalysis.incident_id == incident_id).first()
    dispatches = db.query(Dispatch).filter(Dispatch.incident_id == incident_id).all()
    history = db.query(IncidentHistory).filter(IncidentHistory.incident_id == incident_id).order_by(IncidentHistory.timestamp.asc()).all()

    return {
        "incident": inc,
        "evidence": evidence,
        "ai_analysis": ai_record,
        "dispatches": dispatches,
        "history": history,
    }


@router.post("/{incident_id}/verify")
async def verify_incident(
    incident_id: str,
    payload: IncidentVerifyRequest,
    db: Session = Depends(get_db),
    user = Depends(require_roles(["CONTROL_ROOM_OPERATOR", "admin", "dispatcher"]))
):
    """Control Room Operator verifies or rejects an incoming public incident."""
    inc = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = inc.status
    inc.status = payload.status  # "Verified" or "Rejected"
    inc.verified_by = user.username
    inc.verification_reason = payload.verification_reason

    history = IncidentHistory(
        incident_id=incident_id,
        status_from=old_status,
        status_to=inc.status,
        changed_by=user.username,
        notes=payload.verification_reason,
    )
    db.add(history)
    record_audit(db, user.username, user.role, "VERIFY_INCIDENT", incident_id, f"Transitioned to {inc.status}")
    db.commit()

    await ws_manager.broadcast("INCIDENT_VERIFIED", {
        "incident_id": incident_id,
        "status": inc.status,
        "verified_by": user.username,
        "reason": payload.verification_reason,
    })

    return {"success": True, "incident_id": incident_id, "status": inc.status}


@router.patch("/{incident_id}/status")
async def update_status(
    incident_id: str,
    payload: IncidentUpdateStatus,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Update incident status throughout emergency rescue lifecycle."""
    inc = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = inc.status
    inc.status = payload.status

    if payload.status in ("Resolved", "Cancelled"):
        # Release any assigned vehicles
        vehicles = db.query(Vehicle).filter(Vehicle.active_incident_id == incident_id).all()
        for v in vehicles:
            v.status = "Available"
            v.active_incident_id = None

        dispatches = db.query(Dispatch).filter(
            Dispatch.incident_id == incident_id,
            Dispatch.status.in_(["Active", "En Route", "On Scene", "Transporting Patient", "At Hospital"])
        ).all()
        for d in dispatches:
            d.status = "Completed" if payload.status == "Resolved" else "Cancelled"
            d.completed_at = datetime.utcnow()

    history = IncidentHistory(
        incident_id=incident_id,
        status_from=old_status,
        status_to=payload.status,
        changed_by=user.username,
        notes=payload.notes,
    )
    db.add(history)
    db.commit()

    await ws_manager.broadcast("INCIDENT_STATUS_UPDATED", {
        "incident_id": incident_id,
        "status": payload.status,
        "updated_by": user.username,
    })

    return {"success": True, "incident_id": incident_id, "status": payload.status}


@router.post("/{incident_id}/evidence")
async def upload_evidence(
    incident_id: str,
    file: UploadFile = File(...),
    visual_tags: Optional[str] = Form("[]"),
    db: Session = Depends(get_db)
):
    """Upload photo or video evidence for an active incident."""
    inc = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    filename = f"{incident_id}_{int(time.time())}_{file.filename}"
    filepath = EVIDENCE_DIR / filename

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    evidence = IncidentEvidence(
        incident_id=incident_id,
        file_name=filename,
        file_path=str(filepath),
        evidence_type="video" if filename.endswith((".mp4", ".mov", ".avi")) else "photo",
        visual_tags=visual_tags,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {"success": True, "evidence_id": evidence.id, "file_name": filename}
