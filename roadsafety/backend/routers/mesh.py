"""
roadsafety/backend/routers/mesh.py
==================================
V2X BLE / RF Mesh Protocol Simulator endpoints with CRC-32 validation and CAP JSON.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db, BASE_DIR
from ..models import V2XMeshNode, V2XRelayLog
from ..schemas import MeshSimulateRequest, MeshSimulateResponse

import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.mesh_simulator import MeshProtocolSimulator

router = APIRouter(prefix="/api/mesh", tags=["V2X Mesh Protocol Inspector"])
_mesh_simulator = MeshProtocolSimulator(seed=42)


@router.post("/simulate", response_model=MeshSimulateResponse)
def simulate_v2x_transmission(payload: MeshSimulateRequest, db: Session = Depends(get_db)):
    """Simulate an ad-hoc multi-hop BLE mesh emergency broadcast."""
    res = _mesh_simulator.transmit_sync(
        latitude=payload.latitude,
        longitude=payload.longitude,
        urgency=payload.urgency_index,
        num_hops=payload.hops or 4,
        incident_type=payload.incident_type or "Road Accident",
    )

    # Save to relay log table
    import json
    log = V2XRelayLog(
        total_hops=res.total_hops,
        hops_completed=res.hops_completed,
        delivery_ratio=res.delivery_ratio,
        total_latency_ms=res.total_latency_ms,
        raw_payload_hex=res.raw_payload_hex,
        final_status=res.final_status,
        hop_details_json=json.dumps([
            {"hop": h.hop_number, "relay": h.relay_node_id, "status": h.status, "latency": h.latency_ms}
            for h in res.hop_logs
        ]),
    )
    db.add(log)
    db.commit()

    hop_logs_data = [
        {
            "hop_number": h.hop_number,
            "relay_node_id": h.relay_node_id,
            "status": h.status,
            "latency_ms": round(h.latency_ms, 1),
            "distance_m": h.distance_to_next,
            "rssi_dbm": h.rssi_dbm,
            "retransmits": h.retransmit_count,
            "crc_expected": h.crc_expected,
            "crc_received": h.crc_received,
            "notes": h.notes,
        }
        for h in res.hop_logs
    ]

    return {
        "success": res.success,
        "total_hops": res.total_hops,
        "hops_completed": res.hops_completed,
        "total_latency_ms": res.total_latency_ms,
        "delivery_status": res.final_status,
        "raw_payload_hex": res.raw_payload_hex,
        "cap_alert_json": res.cap_alert_json,
        "hop_logs": hop_logs_data,
    }


@router.get("/nodes")
def list_mesh_nodes(db: Session = Depends(get_db)):
    """Retrieve all smart roadside units and vehicular relay transceivers."""
    return db.query(V2XMeshNode).order_by(V2XMeshNode.node_type).all()


@router.get("/logs")
def list_relay_logs(db: Session = Depends(get_db)):
    """Retrieve recent V2X mesh transmission records."""
    return db.query(V2XRelayLog).order_by(V2XRelayLog.timestamp.desc()).limit(50).all()
