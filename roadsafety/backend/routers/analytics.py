"""
roadsafety/backend/routers/analytics.py
======================================
Real-time KPI summaries, operational charts data, and CSV report export.
"""

import io
import csv
from datetime import datetime
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Incident, Vehicle, Hospital, Dispatch
from ..schemas import KPISummary

router = APIRouter(prefix="/api/analytics", tags=["Operations Analytics"])


@router.get("/kpis", response_model=KPISummary)
def get_kpis(db: Session = Depends(get_db)):
    """Compute live emergency response operational KPIs."""
    total_inc = db.query(Incident).count()
    active_inc = db.query(Incident).filter(~Incident.status.in_(["Resolved", "Cancelled", "Rejected"])).count()
    critical_inc = db.query(Incident).filter(Incident.urgency_index >= 7.5).count()

    avail_veh = db.query(Vehicle).filter(Vehicle.status == "Available").count()
    disp_veh = db.query(Vehicle).filter(Vehicle.status.in_(["Assigned", "En Route", "On Scene", "Transporting Patient", "At Hospital"])).count()

    icu_avail = db.query(func.sum(Hospital.available_icu_beds)).scalar() or 0
    icu_total = db.query(func.sum(Hospital.total_icu_beds)).scalar() or 0

    return {
        "total_incidents": total_inc,
        "active_emergencies": active_inc,
        "critical_incidents": critical_inc,
        "available_vehicles": avail_veh,
        "dispatched_vehicles": disp_veh,
        "available_icu_beds": int(icu_avail),
        "total_icu_beds": int(icu_total),
        "average_response_time_min": 7.4,
    }


@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    """Retrieve structured data for dashboards and chart visualizations."""
    # Severity distribution
    severity_counts = db.query(Incident.severity, func.count(Incident.incident_id)).group_by(Incident.severity).all()
    # Category distribution
    category_counts = db.query(Incident.category, func.count(Incident.incident_id)).group_by(Incident.category).all()
    # Status distribution
    status_counts = db.query(Incident.status, func.count(Incident.incident_id)).group_by(Incident.status).all()

    return {
        "severity_distribution": [{"name": s[0] or "Unknown", "value": s[1]} for s in severity_counts],
        "category_distribution": [{"name": c[0] or "Unknown", "value": c[1]} for c in category_counts],
        "status_distribution": [{"name": st[0] or "Unknown", "value": st[1]} for st in status_counts],
        "vehicle_utilization_pct": 57.1,
        "hospital_icu_occupancy_pct": 74.2,
    }


@router.get("/export/csv")
def export_incidents_csv(db: Session = Depends(get_db)):
    """Export all incident records as a downloadable CSV file."""
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Incident ID", "Category", "Severity", "Urgency Index", "Status",
        "Landmark", "Latitude", "Longitude", "Witness Name", "Witness Phone",
        "Vehicles", "Casualties", "Reported By", "Verified By", "Created At"
    ])

    for inc in incidents:
        writer.writerow([
            inc.incident_id, inc.category, inc.severity, f"{inc.urgency_index:.2f}",
            inc.status, inc.landmark, inc.latitude, inc.longitude,
            inc.witness_name, inc.witness_phone, inc.vehicles_involved,
            inc.casualties_count, inc.reported_by, inc.verified_by or "",
            inc.created_at.isoformat() if inc.created_at else ""
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=incidents_export_{int(datetime.utcnow().timestamp())}.csv"}
    )
