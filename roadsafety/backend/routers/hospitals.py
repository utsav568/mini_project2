"""
roadsafety/backend/routers/hospitals.py
=======================================
Hospital directory, live ICU bed allocation, incoming ambulance telemetry,
bed reservation approvals, and patient handover workflows.
"""

import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import Hospital, HospitalBed, BedReservation, PatientHandoff, Dispatch, Incident
from ..schemas import (
    HospitalResponse, BedReservationCreate, BedReservationResponse,
    BedReservationAction, PatientHandoverCreate
)
from ..security import get_current_user, require_roles, record_audit
from ..websocket_manager import ws_manager

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals & Emergency Beds"])


def generate_reservation_id() -> str:
    return f"RES-{datetime.utcnow().strftime('%Y%m%d')}-{int(time.time() % 10000):04d}"


class HospitalBedUpdate(BaseModel):
    available_icu_beds: Optional[int] = None
    available_general_beds: Optional[int] = None
    status: Optional[str] = None  # Operational, Surge Capacity, Diversion


@router.get("", response_model=List[HospitalResponse])
def get_hospitals(db: Session = Depends(get_db)):
    """Retrieve all regional trauma hospitals with live bed capacity."""
    return db.query(Hospital).order_by(Hospital.category, Hospital.name).all()


@router.get("/{hospital_id}", response_model=HospitalResponse)
def get_hospital(hospital_id: int, db: Session = Depends(get_db)):
    """Retrieve single hospital details."""
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hosp


@router.patch("/{hospital_id}/beds")
async def update_hospital_beds(
    hospital_id: int,
    payload: HospitalBedUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Hospital operator updates live ICU bed availability and operational status."""
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if payload.available_icu_beds is not None:
        hosp.available_icu_beds = max(0, min(hosp.total_icu_beds, payload.available_icu_beds))
    if payload.available_general_beds is not None:
        hosp.available_general_beds = max(0, min(hosp.total_general_beds, payload.available_general_beds))
    if payload.status:
        hosp.status = payload.status

    record_audit(db, user.username, user.role, "UPDATE_HOSPITAL_BEDS", hosp.name, f"ICU: {hosp.available_icu_beds}")
    db.commit()

    await ws_manager.broadcast("HOSPITAL_CAPACITY_UPDATED", {
        "hospital_id": hosp.id,
        "name": hosp.name,
        "available_icu_beds": hosp.available_icu_beds,
        "available_general_beds": hosp.available_general_beds,
        "status": hosp.status,
    })

    return {"success": True, "hospital": hosp}


@router.post("/reserve", response_model=BedReservationResponse)
async def reserve_bed(
    payload: BedReservationCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Transactionally reserve a trauma/ICU bed.
    Prevents negative bed counts and double booking.
    """
    hosp = db.query(Hospital).filter(Hospital.id == payload.hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if hosp.status == "Diversion":
        raise HTTPException(status_code=400, detail=f"Cannot reserve bed at {hosp.name}: Facility on Diversion")

    if hosp.available_icu_beds <= 0:
        raise HTTPException(status_code=400, detail=f"Zero ICU beds available at {hosp.name} (0/{hosp.total_icu_beds})")

    # Check for duplicate active reservation for same patient
    existing = db.query(BedReservation).filter(
        BedReservation.hospital_id == payload.hospital_id,
        BedReservation.incident_id == payload.incident_id,
        BedReservation.patient_identifier == payload.patient_identifier,
        BedReservation.patient_handover_status == "Pending Arrival"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Active reservation already exists ({existing.reservation_id})")

    res_id = generate_reservation_id()
    reservation = BedReservation(
        reservation_id=res_id,
        hospital_id=hosp.id,
        incident_id=payload.incident_id,
        dispatch_id=payload.dispatch_id,
        patient_identifier=payload.patient_identifier,
        bed_type=payload.bed_type or "ICU",
        reserved_by=user.username,
        patient_handover_status="Pending Arrival",
        status="Pending",
        notes=payload.notes,
    )
    db.add(reservation)

    # Safely decrement available bed count
    hosp.available_icu_beds = max(0, hosp.available_icu_beds - 1)

    record_audit(db, user.username, user.role, "RESERVE_BED", res_id, f"Reserved ICU bed at {hosp.name}")
    db.commit()
    db.refresh(reservation)

    await ws_manager.broadcast("BED_RESERVED", {
        "reservation_id": reservation.reservation_id,
        "hospital_id": hosp.id,
        "hospital_name": hosp.name,
        "incident_id": payload.incident_id,
        "patient_identifier": payload.patient_identifier,
        "available_icu_beds": hosp.available_icu_beds,
    })

    return reservation


@router.post("/reservation/{reservation_id}/action")
async def handle_reservation_action(
    reservation_id: str,
    payload: BedReservationAction,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Hospital action on bed reservation:
    - accept: Accepted
    - reject: Rejected (releases reserved bed back to hospital count)
    - admit: Patient Admitted
    - release: Released (restores bed count)
    """
    res = db.query(BedReservation).filter(BedReservation.reservation_id == reservation_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")

    hosp = db.query(Hospital).filter(Hospital.id == res.hospital_id).first()
    action = payload.action.lower()

    if action == "accept":
        res.status = "Accepted"
    elif action == "reject":
        res.status = "Rejected"
        res.patient_handover_status = "Rejected"
        res.rejection_reason = payload.reason or "Hospital at critical capacity"
        # Restore reserved bed
        if hosp:
            hosp.available_icu_beds = min(hosp.total_icu_beds, hosp.available_icu_beds + 1)
    elif action == "admit":
        res.patient_handover_status = "Patient Admitted"
        res.status = "Completed"
        res.handover_at = datetime.utcnow()
    elif action in ("release", "transfer"):
        res.patient_handover_status = "Released" if action == "release" else "Transferred"
        if hosp:
            hosp.available_icu_beds = min(hosp.total_icu_beds, hosp.available_icu_beds + 1)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    record_audit(db, user.username, user.role, "RESERVATION_ACTION", res.reservation_id, f"Action: {action}")
    db.commit()

    await ws_manager.broadcast("RESERVATION_UPDATED", {
        "reservation_id": res.reservation_id,
        "action": action,
        "status": res.status,
        "patient_handover_status": res.patient_handover_status,
        "hospital_id": hosp.id if hosp else None,
        "available_icu_beds": hosp.available_icu_beds if hosp else None,
    })

    return {
        "success": True,
        "reservation_id": res.reservation_id,
        "action": action,
        "status": res.status,
    }


@router.get("/{hospital_id}/incoming")
def get_incoming_ambulances(hospital_id: int, db: Session = Depends(get_db)):
    """Retrieve all incoming dispatches currently transporting patients to this hospital."""
    incoming = db.query(Dispatch).filter(
        Dispatch.destination_hospital_id == hospital_id,
        Dispatch.status.in_(["En Route", "On Scene", "Transporting Patient", "At Hospital"])
    ).all()

    results = []
    for d in incoming:
        inc = db.query(Incident).filter(Incident.incident_id == d.incident_id).first()
        results.append({
            "dispatch": d,
            "incident": inc,
        })
    return results


@router.get("/{hospital_id}/reservations")
def get_hospital_reservations(hospital_id: int, db: Session = Depends(get_db)):
    """Retrieve all active bed reservations for this hospital."""
    return db.query(BedReservation).filter(
        BedReservation.hospital_id == hospital_id
    ).order_by(BedReservation.reserved_at.desc()).limit(50).all()
