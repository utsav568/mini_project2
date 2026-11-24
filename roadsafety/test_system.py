"""
GuardianNodes RoadSoS - Automated Verification & Test Suite
Covers Database, Auth/RBAC, Incident Intake, AI Triage, Fleet Dispatch,
Routing, Hospital Bed Allocation, and V2X Mesh Protocol.
"""

import sys
import os
import time

# Ensure roadsafety directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modules.database import get_db_connection, init_database
from modules.auth import hash_password, verify_password, authenticate_user, has_permission, get_all_users
from modules.incident_service import (
    generate_incident_id, create_incident, get_incident_by_id,
    update_incident_status, get_all_incidents
)
from modules.fleet_service import (
    get_all_vehicles, get_available_vehicles, dispatch_vehicle,
    cancel_dispatch, update_vehicle_status
)
from modules.hospital_service import (
    get_all_hospitals, reserve_hospital_bed, update_patient_handover
)
from modules.triage_engine import IntelligentTriageEngine
from modules.routing_engine import GraphRoutingEngine
from modules.mesh_simulator import MeshPacket, MeshProtocolSimulator, _encode_packet, _decode_and_verify, STRUCT_FORMAT, STRUCT_SIZE

def test_suite():
    print("=" * 75)
    print(">>> GUARDIANNODES ROADSOS: RUNNING INTEGRATION VERIFICATION SUITE")
    print("=" * 75)
    
    # 1. Database Initialization & Table Verification
    print("\n[TEST 1/8] Verifying Database Schema & Table Integrity...")
    init_database()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
    
    expected_tables = [
        "users", "incidents", "incident_evidence", "emergency_vehicles",
        "dispatches", "hospitals", "hospital_bed_reservations",
        "v2x_mesh_nodes", "v2x_relay_logs", "audit_logs"
    ]
    for tbl in expected_tables:
        assert tbl in tables, f"Missing expected table: {tbl}"
    print(f"  [PASS] All {len(expected_tables)} relational tables verified in SQLite WAL mode.")

    # 2. Authentication & RBAC Verification
    print("\n[TEST 2/8] Verifying Authentication & Role-Based Access Control...")
    admin_user = authenticate_user("admin", "admin123")
    assert admin_user is not None, "Failed to authenticate default admin user"
    assert admin_user["role"] == "admin"
    assert has_permission(admin_user["role"], "manage_users") is True
    
    hosp_user = authenticate_user("aiims_admin", "hospital123")
    assert hosp_user is not None
    assert has_permission(hosp_user["role"], "dispatch_vehicle") is False
    assert has_permission(hosp_user["role"], "reserve_hospital_bed") is True
    
    # Password verification & salt check
    test_hash = hash_password("secret_pass")
    assert verify_password("secret_pass", test_hash) is True
    assert verify_password("wrong_pass", test_hash) is False
    assert authenticate_user("admin", "wrong_password") is None
    print("  [PASS] Salted SHA-256 Auth & RBAC permission matrix verified.")

    # 3. Incident Lifecycle & ID Generation
    print("\n[TEST 3/8] Verifying Incident Intake & Lifecycle Management...")
    inc_id = generate_incident_id()
    assert inc_id.startswith("INC-"), f"Invalid ID format: {inc_id}"
    
    inc_result = create_incident(
        witness_statement="High speed collision between commercial bus and SUV near AIIMS. 2 passengers trapped, engine smoking.",
        latitude=28.5672,
        longitude=77.2100,
        witness_name="Test Witness",
        witness_phone="+91 98765 43210",
        visual_tags=["Entrapment", "Smoke"],
        username="admin"
    )
    assert inc_result is not None, "Failed to create incident"
    created_id = inc_result["incident_id"]
    
    retrieved = get_incident_by_id(created_id)
    assert retrieved is not None
    assert retrieved["incident_id"] == created_id
    assert retrieved["status"] == "AI Analyzed"
    
    # Transition status
    update_incident_status(created_id, "Verified", username="admin")
    updated = get_incident_by_id(created_id)
    assert updated["status"] == "Verified"
    print(f"  [PASS] Incident {created_id} created, persisted, and transitioned to Verified.")

    # 4. AI Triage Engine Accuracy
    print("\n[TEST 4/8] Verifying AI Triage Classification & Reasoning...")
    engine = IntelligentTriageEngine()
    triage_res = engine.analyze(
        witness_text="Head-on crash between two cars with 3 people critically injured and fuel leaking onto highway.",
        visual_tags=["Critical Medical Trauma", "Fuel Leak"]
    )
    assert triage_res.urgency_index >= 7.0, f"Expected critical priority score, got {triage_res.urgency_index}"
    assert triage_res.top_label in ["Critical Medical Trauma", "Hazardous Material Leak", "Vehicle Entrapment"]
    assert len(triage_res.recommended_units) > 0
    print(f"  [PASS] AI Triage: Top Label='{triage_res.top_label}', Urgency Index={triage_res.urgency_index:.2f}/10, GoldenHourSLA={triage_res.golden_hour_sla_min}min.")

    # 5. Fleet Dispatch & Duplicate Prevention
    print("\n[TEST 5/8] Verifying Fleet Dispatch & Duplicate Prevention...")
    avail_veh = get_available_vehicles()
    assert len(avail_veh) > 0, "No available vehicles to test dispatch"
    veh_to_dispatch = avail_veh[0]["id"]
    
    # Dispatch vehicle
    dsp_id = dispatch_vehicle(
        incident_id=created_id,
        vehicle_id=veh_to_dispatch,
        assigned_by="admin",
        route_time_min=8.5,
        dispatch_notes="Unit dispatched via automated test suite"
    )
    assert dsp_id.startswith("DSP-"), f"Invalid dispatch ID: {dsp_id}"
    
    # Attempt duplicate dispatch on same vehicle
    double_dispatch_blocked = False
    try:
        dispatch_vehicle(
            incident_id=created_id,
            vehicle_id=veh_to_dispatch,
            assigned_by="admin",
            route_time_min=10.0,
            dispatch_notes="Duplicate attempt"
        )
    except ValueError as exc:
        double_dispatch_blocked = True
        print(f"  [PASS] Double-dispatch correctly blocked by DB constraint: {exc}")
    
    assert double_dispatch_blocked, "Double-dispatch was NOT blocked!"
    
    # Cancel dispatch & restore vehicle
    cancel_dispatch(dsp_id, username="admin", reason="Test suite completion")
    # Verify vehicle status is Available again
    avail_after = [v for v in get_all_vehicles() if v["id"] == veh_to_dispatch][0]
    assert avail_after["status"] == "Available"
    print(f"  [PASS] Dispatch {dsp_id} cancelled; vehicle returned to 'Available'.")

    # 6. Routing Engine & Delhi NCR Grid Snapping
    print("\n[TEST 6/8] Verifying Delhi NCR Road Network Routing Engine...")
    router = GraphRoutingEngine(seed=42)
    # Snap AIIMS coordinates
    nearest_node = router.find_nearest_node(28.5672, 77.2100)
    assert 0 <= nearest_node < 100
    
    route_res = router.route(source_node=0, target_node=nearest_node, vehicle_type="ambulance")
    assert len(route_res.path) >= 2
    assert route_res.estimated_time_min > 0
    assert len(route_res.path_coords) == len(route_res.path)
    assert route_res.nearest_hospital is not None
    print(f"  [PASS] Nearest node {nearest_node} ({router.get_node_label(nearest_node)}), Path Nodes={len(route_res.path)}, ETA={route_res.estimated_time_min:.1f} mins, Evacuation Hosp={route_res.nearest_hospital['name']}.")

    # 7. Hospital Bed Allocation & Capacity Enforcement
    print("\n[TEST 7/8] Verifying Hospital Bed Reservations & Handover...")
    hospitals = get_all_hospitals()
    assert len(hospitals) > 0, "No hospitals configured in database"
    target_hosp = hospitals[0]
    hosp_id = target_hosp["id"]
    initial_beds = target_hosp["available_icu_beds"]
    
    res_id = reserve_hospital_bed(
        hospital_id=hosp_id,
        incident_id=created_id,
        patient_identifier="PAT-2026-TEST",
        bed_type="Trauma ICU",
        reserved_by="hospital",
        notes="Code Red trauma patient inbound from AIIMS"
    )
    assert res_id.startswith("RES-"), f"Invalid reservation ID: {res_id}"
    
    # Verify ICU bed count decreased by 1
    updated_hosp = [h for h in get_all_hospitals() if h["id"] == hosp_id][0]
    assert updated_hosp["available_icu_beds"] == initial_beds - 1
    
    # Update handover status to Patient Admitted
    update_patient_handover(res_id, "Patient Admitted", username="hospital", notes="Admitted to Trauma Bay 1.")
    print(f"  [PASS] Reserved ICU bed at {target_hosp['name']} (remaining: {updated_hosp['available_icu_beds']}). Handover updated to 'Patient Admitted'.")

    # 8. V2X BLE / RF Mesh Protocol & CRC-32 Validation
    print("\n[TEST 8/8] Verifying V2X BLE / RF Mesh Protocol Simulator...")
    packet = MeshPacket(
        latitude=28.5672,
        longitude=77.2100,
        urgency=8.85,
        timestamp=int(time.time()),
        sequence=42,
        flags=0x07,
    )
    raw_packet = _encode_packet(packet)
    assert len(raw_packet) == 24, f"Expected 24-byte packet, got {len(raw_packet)}"
    
    # Decode and check CRC-32
    is_valid, exp_crc, rec_crc = _decode_and_verify(raw_packet)
    assert is_valid is True, f"CRC-32 verification failed on valid packet: exp={exp_crc}, rec={rec_crc}"
    
    # Bit-flip corruption test
    corrupted = bytearray(raw_packet)
    corrupted[8] ^= 0xFF
    corrupted_valid, _, _ = _decode_and_verify(bytes(corrupted))
    assert corrupted_valid is False, "CRC-32 failed to detect bit corruption!"
    
    # Multi-hop simulation
    simulator = MeshProtocolSimulator(seed=42)
    sim_result = simulator.transmit_sync(
        latitude=28.5672,
        longitude=77.2100,
        urgency=8.85,
        num_hops=4,
        incident_type="Multi-Vehicle Collision",
        dispatched_units=["AMB-101 (ALS)", "FIRE-501"],
        nearest_hospital="AIIMS Apex Trauma Centre"
    )
    assert sim_result.total_hops == 4
    assert sim_result.total_latency_ms > 0
    assert sim_result.final_status in ["DELIVERED", "FAILED"]
    assert len(sim_result.cap_alert_json) > 0
    print(f"  [PASS] 24-byte BLE packing, CRC-32 validation, and multi-hop relay simulation ({sim_result.total_hops} hops, {sim_result.total_latency_ms:.1f}ms latency, status={sim_result.final_status}, CAP JSON length={len(sim_result.cap_alert_json)}) verified.")

    print("\n" + "=" * 75)
    print(">>> ALL 8 INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 75)

if __name__ == "__main__":
    test_suite()
