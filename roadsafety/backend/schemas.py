"""
roadsafety/backend/schemas.py
=============================
Pydantic v2 schemas for request validation, data serialization, and response typing.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------

class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    badge_number: Optional[str] = None
    phone: Optional[str] = None
    hospital_id: Optional[int] = None
    vehicle_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    badge_number: Optional[str] = None
    phone: Optional[str] = None
    hospital_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Incident Schemas
# ---------------------------------------------------------------------------

class IncidentPublicCreate(BaseModel):
    witness_statement: str
    latitude: float
    longitude: float
    witness_name: Optional[str] = "Anonymous Citizen"
    witness_phone: Optional[str] = "N/A"
    category: Optional[str] = "Road Collision"
    reported_casualties: Optional[int] = 0
    vehicles_count: Optional[int] = 1
    hazards: Optional[List[str]] = []
    visual_tags: Optional[List[str]] = []


class IncidentVerifyRequest(BaseModel):
    status: str  # "Verified" or "Rejected"
    verification_reason: Optional[str] = "Verified by Control Room Operator"


class IncidentUpdateStatus(BaseModel):
    status: str
    notes: Optional[str] = None


class IncidentResponse(BaseModel):
    incident_id: str
    witness_name: str
    witness_phone: str
    witness_statement: str
    category: str
    severity: str
    latitude: float
    longitude: float
    grid_node: int
    landmark: str
    status: str
    urgency_index: float
    golden_hour_sla_min: float
    ai_analysis_reasoning: Optional[str] = None
    vehicles_involved: int
    casualties_count: int
    hazards_detected: Optional[str] = "[]"
    recommended_units: Optional[str] = "[]"
    reported_by: str
    verified_by: Optional[str] = None
    verification_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AI Triage Schemas
# ---------------------------------------------------------------------------

class AIAnalyzeRequest(BaseModel):
    text: str
    vehicles_hint: Optional[int] = None
    casualties_hint: Optional[int] = None
    hazards_hint: Optional[List[str]] = None
    visual_tags: Optional[List[str]] = None


class AIAnalysisResponse(BaseModel):
    category: str
    vehicle_count: int
    reported_casualties: int
    fire_mentioned: bool
    hazard_level: str
    severity: str
    urgency_index: float
    golden_hour_sla_min: float
    recommended_resources: List[str]
    explanation: str
    confidence_score: float


# ---------------------------------------------------------------------------
# Vehicle & Dispatch Schemas
# ---------------------------------------------------------------------------

class VehicleResponse(BaseModel):
    id: int
    callsign: str
    vehicle_type: str
    label: str
    station_base: str
    current_lat: float
    current_lon: float
    current_node: int
    status: str
    crew_lead: str
    fuel_level_pct: int
    active_incident_id: Optional[str] = None
    active_driver_id: Optional[int] = None

    class Config:
        from_attributes = True


class DispatchCreate(BaseModel):
    incident_id: str
    vehicle_id: int
    notes: Optional[str] = "Dispatched via CAD"
    destination_hospital_id: Optional[int] = None


class DriverGPSUpdate(BaseModel):
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = 45.0
    heading_deg: Optional[float] = 0.0


class DispatchActionRequest(BaseModel):
    action: str  # "accept", "reject", "en_route", "on_scene", "transporting", "at_hospital", "complete"
    reason: Optional[str] = None
    notes: Optional[str] = None
    destination_hospital_id: Optional[int] = None


class DispatchResponse(BaseModel):
    dispatch_id: str
    incident_id: str
    vehicle_id: int
    driver_id: Optional[int] = None
    assigned_by: str
    status: str
    route_time_min: float
    route_distance_km: float
    destination_hospital_id: Optional[int] = None
    eta_min: float
    dispatch_notes: Optional[str] = None
    assigned_at: datetime
    en_route_at: Optional[datetime] = None
    on_scene_at: Optional[datetime] = None
    at_hospital_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Hospital & Bed Reservation Schemas
# ---------------------------------------------------------------------------

class HospitalResponse(BaseModel):
    id: int
    name: str
    category: str
    address: str
    latitude: float
    longitude: float
    grid_node: int
    total_icu_beds: int
    available_icu_beds: int
    total_general_beds: int
    available_general_beds: int
    trauma_bays: int
    blood_bank_status: str
    emergency_hotline: str
    status: str

    class Config:
        from_attributes = True


class BedReservationCreate(BaseModel):
    hospital_id: int
    incident_id: str
    patient_identifier: str
    bed_type: Optional[str] = "ICU"
    notes: Optional[str] = ""
    dispatch_id: Optional[str] = None


class BedReservationAction(BaseModel):
    action: str  # "accept", "reject", "admit", "transfer", "release"
    reason: Optional[str] = None
    notes: Optional[str] = None


class PatientHandoverCreate(BaseModel):
    reservation_id: str
    patient_condition: str
    receiving_doctor: str
    handover_notes: Optional[str] = ""


class BedReservationResponse(BaseModel):
    reservation_id: str
    hospital_id: int
    incident_id: str
    dispatch_id: Optional[str] = None
    patient_identifier: str
    bed_type: str
    reserved_by: str
    patient_handover_status: str
    status: str
    notes: Optional[str] = None
    reserved_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Routing & Mesh Schemas
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    source_lat: float
    source_lon: float
    dest_lat: float
    dest_lon: float
    vehicle_type: Optional[str] = "ambulance"


class RouteResponse(BaseModel):
    route_found: bool
    path_nodes: List[int]
    path_coords: List[List[float]]
    total_distance_km: float
    estimated_time_min: float
    source_label: str
    dest_label: str
    nearest_hospital: Optional[Dict[str, Any]] = None


class MeshSimulateRequest(BaseModel):
    latitude: float
    longitude: float
    urgency_index: float
    hops: Optional[int] = 4
    incident_type: Optional[str] = "Road Accident"


class MeshSimulateResponse(BaseModel):
    success: bool
    total_hops: int
    hops_completed: int
    total_latency_ms: float
    delivery_status: str
    raw_payload_hex: str
    cap_alert_json: str
    hop_logs: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Analytics Schemas
# ---------------------------------------------------------------------------

class KPISummary(BaseModel):
    total_incidents: int
    active_emergencies: int
    critical_incidents: int
    available_vehicles: int
    dispatched_vehicles: int
    available_icu_beds: int
    total_icu_beds: int
    average_response_time_min: float
