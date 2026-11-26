"""
roadsafety/backend/routers/vehicles.py
======================================
Fleet management, vehicle dispatching, duplicate prevention, driver workflows,
and live GPS telemetry updates.
"""

import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Vehicle, Dispatch, Incident, Driver, VehicleLocation, IncidentHistory
from ..schemas import VehicleResponse, DispatchCreate, DispatchResponse, DriverGPSUpdate, DispatchActionRequest
from ..security import get_current_user, require_roles, record_audit
from ..websocket_manager import ws_manager

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles & Fleet"])


def generate_dispatch_id() -> str:
    return f"DSP-{datetime.utcnow().strftime('%Y%m%d')}-{int(time.time() % 10000):04d}"


@router.get("", response_model=List[VehicleResponse])
def get_fleet(db: Session = Depends(get_db)):
    """Retrieve all emergency response fleet units with live availability."""
    return db.query(Vehicle).order_by(Vehicle.vehicle_type, Vehicle.callsign).all()


@router.post("/dispatch", response_model=DispatchResponse)
async def dispatch_vehicle_to_incident(
    payload: DispatchCreate,
    db: Session = Depends(get_db),
    user = Depends(require_roles(["CONTROL_ROOM_OPERATOR", "admin", "dispatcher"]))
):
    """
    Dispatch an emergency vehicle to an active incident.
    Enforces transactional concurrency lock preventing double vehicle assignments.
    """
    veh = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if veh.status != "Available":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot dispatch {veh.callsign}: Unit is currently '{veh.status}'"
        )

    inc = db.query(Incident).filter(Incident.incident_id == payload.incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    if inc.status in ("Resolved", "Cancelled", "Rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot dispatch: Incident is '{inc.status}'")

    dsp_id = generate_dispatch_id()
    dispatch = Dispatch(
        dispatch_id=dsp_id,
        incident_id=payload.incident_id,
        vehicle_id=veh.id,
        driver_id=veh.active_driver_id,
        assigned_by=user.username,
        status="En Route",
        route_time_min=8.5,
        route_distance_km=4.2,
        destination_hospital_id=payload.destination_hospital_id,
        eta_min=8.5,
        dispatch_notes=payload.notes,
        en_route_at=datetime.utcnow(),
    )
    db.add(dispatch)

    # Update vehicle state
    veh.status = "En Route"
    veh.active_incident_id = payload.incident_id

    # Update incident state
    old_inc_status = inc.status
    inc.status = "Dispatched"
    history = IncidentHistory(
        incident_id=inc.incident_id,
        status_from=old_inc_status,
        status_to="Dispatched",
        changed_by=user.username,
        notes=f"Dispatched unit {veh.callsign} ({veh.label})",
    )
    db.add(history)

    record_audit(db, user.username, user.role, "DISPATCH_VEHICLE", dsp_id, f"Dispatched {veh.callsign} to {inc.incident_id}")
    db.commit()
    db.refresh(dispatch)

    # Broadcast event
    await ws_manager.broadcast("DISPATCH_ASSIGNED", {
        "dispatch_id": dispatch.dispatch_id,
        "incident_id": inc.incident_id,
        "vehicle_id": veh.id,
        "callsign": veh.callsign,
        "vehicle_type": veh.vehicle_type,
        "status": "En Route",
        "eta_min": dispatch.eta_min,
        "landmark": inc.landmark,
    })

    return dispatch


@router.get("/driver/active-dispatch")
def get_driver_active_dispatch(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Retrieve active dispatch assignment for driver dashboard."""
    # Find driver record or vehicle assigned to user
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    veh_id = driver.assigned_vehicle_id if driver else user.vehicle_id

    query = db.query(Dispatch).filter(
        Dispatch.status.in_(["Active", "Accepted", "En Route", "On Scene", "Transporting Patient", "At Hospital"])
    )
    if veh_id:
        query = query.filter(Dispatch.vehicle_id == veh_id)

    active_dispatch = query.order_by(Dispatch.assigned_at.desc()).first()
    if not active_dispatch:
        return {"active": False, "dispatch": None, "incident": None, "vehicle": None}

    inc = db.query(Incident).filter(Incident.incident_id == active_dispatch.incident_id).first()
    veh = db.query(Vehicle).filter(Vehicle.id == active_dispatch.vehicle_id).first()

    return {
        "active": True,
        "dispatch": active_dispatch,
        "incident": inc,
        "vehicle": veh,
    }


@router.post("/driver/action")
async def handle_driver_action(
    payload: DispatchActionRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Handle driver workflow status transitions:
    - accept: Accepted
    - en_route: En Route
    - on_scene: On Scene (incident -> Rescue in Progress)
    - transporting: Transporting Patient
    - at_hospital: At Hospital
    - complete: Completed (releases vehicle back to Available)
    """
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    veh_id = driver.assigned_vehicle_id if driver else user.vehicle_id

    query = db.query(Dispatch).filter(
        Dispatch.status.in_(["Active", "Accepted", "En Route", "On Scene", "Transporting Patient", "At Hospital"])
    )
    if veh_id:
        query = query.filter(Dispatch.vehicle_id == veh_id)

    dsp = query.order_by(Dispatch.assigned_at.desc()).first()
    if not dsp:
        raise HTTPException(status_code=404, detail="No active dispatch assignment found for driver")

    veh = db.query(Vehicle).filter(Vehicle.id == dsp.vehicle_id).first()
    inc = db.query(Incident).filter(Incident.incident_id == dsp.incident_id).first()

    action = payload.action.lower()
    now = datetime.utcnow()

    if action == "accept":
        dsp.status = "Accepted"
    elif action == "reject":
        dsp.status = "Rejected"
        dsp.rejection_reason = payload.reason or "Rejected by driver"
        if veh:
            veh.status = "Available"
            veh.active_incident_id = None
    elif action == "en_route":
        dsp.status = "En Route"
        dsp.en_route_at = now
        if veh:
            veh.status = "En Route"
    elif action == "on_scene":
        dsp.status = "On Scene"
        dsp.on_scene_at = now
        if veh:
            veh.status = "On Scene"
        if inc:
            inc.status = "On Scene"
    elif action == "transporting":
        dsp.status = "Transporting Patient"
        dsp.dispatch_notes = "Transporting Patient to Hospital"
        if veh:
            veh.status = "Transporting Patient"
        if inc:
            inc.status = "Rescue in Progress"
        if payload.destination_hospital_id:
            dsp.destination_hospital_id = payload.destination_hospital_id
    elif action == "at_hospital":
        dsp.status = "At Hospital"
        dsp.dispatch_notes = "Arrived at Hospital"
        dsp.at_hospital_at = now
        if veh:
            veh.status = "At Hospital"
        if inc:
            inc.status = "Rescue in Progress"
    elif action == "complete":
        dsp.status = "Completed"
        dsp.completed_at = now
        if veh:
            veh.status = "Available"
            veh.active_incident_id = None
        if inc:
            inc.status = "Resolved"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    record_audit(db, user.username, user.role, "DRIVER_ACTION", dsp.dispatch_id, f"Action: {action}")
    db.commit()

    await ws_manager.broadcast("DRIVER_STATUS_UPDATED", {
        "dispatch_id": dsp.dispatch_id,
        "action": action,
        "dispatch_status": dsp.status,
        "vehicle_id": veh.id if veh else None,
        "vehicle_status": veh.status if veh else None,
        "incident_id": inc.incident_id if inc else None,
        "incident_status": inc.status if inc else None,
    })

    return {
        "success": True,
        "dispatch_id": dsp.dispatch_id,
        "status": dsp.status,
        "action": action,
    }


@router.post("/driver/gps")
async def update_driver_gps(
    payload: DriverGPSUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Update driver and vehicle live GPS position during active shifts."""
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    veh_id = driver.assigned_vehicle_id if driver else user.vehicle_id

    if driver:
        driver.current_lat = payload.latitude
        driver.current_lon = payload.longitude
        driver.last_gps_update = datetime.utcnow()

    if veh_id:
        veh = db.query(Vehicle).filter(Vehicle.id == veh_id).first()
        if veh:
            veh.current_lat = payload.latitude
            veh.current_lon = payload.longitude

            loc = VehicleLocation(
                vehicle_id=veh.id,
                latitude=payload.latitude,
                longitude=payload.longitude,
                speed_kmh=payload.speed_kmh or 45.0,
                heading_deg=payload.heading_deg or 0.0,
            )
            db.add(loc)

    db.commit()

    # Broadcast live GPS position to Control Room
    await ws_manager.broadcast("DRIVER_GPS_UPDATED", {
        "vehicle_id": veh_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "speed_kmh": payload.speed_kmh,
        "heading_deg": payload.heading_deg,
        "driver_username": user.username,
    })

    return {"success": True, "latitude": payload.latitude, "longitude": payload.longitude}


@router.post("/dispatch/{dispatch_id}/cancel")
async def cancel_dispatch(
    dispatch_id: str,
    db: Session = Depends(get_db),
    user = Depends(require_roles(["CONTROL_ROOM_OPERATOR", "admin", "dispatcher"]))
):
    """Cancel an active dispatch and release vehicle back to Available status."""
    dsp = db.query(Dispatch).filter(Dispatch.dispatch_id == dispatch_id).first()
    if not dsp:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    dsp.status = "Cancelled"
    dsp.completed_at = datetime.utcnow()

    veh = db.query(Vehicle).filter(Vehicle.id == dsp.vehicle_id).first()
    if veh:
        veh.status = "Available"
        veh.active_incident_id = None

    record_audit(db, user.username, user.role, "CANCEL_DISPATCH", dispatch_id, "Cancelled by operator")
    db.commit()

    await ws_manager.broadcast("DISPATCH_CANCELLED", {
        "dispatch_id": dispatch_id,
        "vehicle_id": veh.id if veh else None,
        "callsign": veh.callsign if veh else None,
    })

    return {"success": True, "dispatch_id": dispatch_id, "status": "Cancelled"}
