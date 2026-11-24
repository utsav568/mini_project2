"""
roadsafety/backend/models.py
============================
SQLAlchemy ORM models defining the 18 core relational entities for GuardianNodes RoadSoS.
Supports UUID and primary keys, timestamps, and foreign key relationships.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from .database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), index=True, nullable=False)  # SUPER_ADMIN, CONTROL_ROOM_OPERATOR, CITIZEN, AMBULANCE_DRIVER, HOSPITAL_OPERATOR, etc.
    badge_number = Column(String(64), nullable=True)
    phone = Column(String(32), nullable=True)
    hospital_id = Column(Integer, nullable=True)
    vehicle_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    citizen_profile = relationship("CitizenProfile", back_populates="user", uselist=False)
    driver_profile = relationship("Driver", back_populates="user", uselist=False)


class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=False)
    emergency_contact = Column(String(32), nullable=True)
    language_preference = Column(String(8), default="en")  # en, hi
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="citizen_profile")


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(32), primary_key=True, index=True, nullable=False)
    witness_name = Column(String(128), default="Anonymous Citizen")
    witness_phone = Column(String(32), default="N/A")
    witness_statement = Column(Text, nullable=False)
    sensor_payload = Column(Text, default="{}")
    category = Column(String(64), nullable=False, default="Road Collision")
    severity = Column(String(32), default="Moderate")  # Critical, Severe, Moderate, Minor
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    grid_node = Column(Integer, default=0)
    landmark = Column(String(128), default="Central Delhi Junction")
    status = Column(String(32), index=True, default="Reported")  # Reported, Under Verification, AI Analyzed, Verified, Response Dispatched, En Route, On Scene, Resolved, Cancelled, Rejected
    urgency_index = Column(Float, default=5.0)  # 1.00 to 10.00
    golden_hour_sla_min = Column(Float, default=15.0)
    ai_analysis_reasoning = Column(Text, nullable=True)
    extracted_entities = Column(Text, default="{}")
    recommended_units = Column(Text, default="[]")
    vehicles_involved = Column(Integer, default=1)
    casualties_count = Column(Integer, default=0)
    hazards_detected = Column(Text, default="[]")
    reported_by = Column(String(64), default="citizen")
    verified_by = Column(String(64), nullable=True)
    verification_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence = relationship("IncidentEvidence", back_populates="incident", cascade="all, delete-orphan")
    dispatches = relationship("Dispatch", back_populates="incident")
    reservations = relationship("BedReservation", back_populates="incident")


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(32), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    file_name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    evidence_type = Column(String(32), default="photo")  # photo, video, sensor
    visual_tags = Column(Text, default="[]")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="evidence")


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(32), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    category = Column(String(64), nullable=False)
    vehicle_count = Column(Integer, default=1)
    reported_casualties = Column(Integer, default=0)
    fire_mentioned = Column(Boolean, default=False)
    hazard_level = Column(String(32), default="Moderate")
    severity = Column(String(32), default="Moderate")
    recommended_resources = Column(Text, default="[]")
    explanation = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.85)
    raw_response = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class Vehicle(Base):
    __tablename__ = "emergency_vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    callsign = Column(String(32), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(32), index=True, nullable=False)  # ambulance, advanced_life_support, fire_engine, police_car, rescue_van, medical_helicopter
    label = Column(String(128), nullable=False)
    station_base = Column(String(128), nullable=False)
    current_lat = Column(Float, nullable=False)
    current_lon = Column(Float, nullable=False)
    current_node = Column(Integer, default=0)
    status = Column(String(32), index=True, default="Available")  # Available, Assigned, En Route, On Scene, Transporting Patient, At Hospital, Out of Service
    crew_lead = Column(String(128), nullable=False)
    fuel_level_pct = Column(Integer, default=100)
    active_incident_id = Column(String(32), nullable=True)
    active_driver_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dispatches = relationship("Dispatch", back_populates="vehicle")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(128), nullable=False)
    badge_number = Column(String(64), nullable=False)
    phone = Column(String(32), nullable=False)
    assigned_vehicle_id = Column(Integer, ForeignKey("emergency_vehicles.id"), nullable=True)
    duty_status = Column(String(32), default="Available")  # Available, Busy, Off Duty
    current_lat = Column(Float, default=28.6139)
    current_lon = Column(Float, default=77.2090)
    last_gps_update = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="driver_profile")
    dispatches = relationship("Dispatch", back_populates="driver")


class Dispatch(Base):
    __tablename__ = "dispatches"

    dispatch_id = Column(String(32), primary_key=True, index=True, nullable=False)
    incident_id = Column(String(32), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("emergency_vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    assigned_by = Column(String(64), nullable=False)
    status = Column(String(32), index=True, default="Active")  # Active, Accepted, Rejected, En Route, On Scene, Transporting Patient, At Hospital, Completed, Cancelled
    route_time_min = Column(Float, default=10.0)
    route_distance_km = Column(Float, default=5.0)
    route_path_nodes = Column(Text, default="[]")
    destination_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    eta_min = Column(Float, default=10.0)
    dispatch_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    en_route_at = Column(DateTime, nullable=True)
    on_scene_at = Column(DateTime, nullable=True)
    at_hospital_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="dispatches")
    vehicle = relationship("Vehicle", back_populates="dispatches")
    driver = relationship("Driver", back_populates="dispatches")


class VehicleLocation(Base):
    __tablename__ = "vehicle_locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("emergency_vehicles.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmh = Column(Float, default=0.0)
    heading_deg = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), unique=True, index=True, nullable=False)
    category = Column(String(64), nullable=False)
    address = Column(String(256), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    grid_node = Column(Integer, default=0)
    total_icu_beds = Column(Integer, default=20)
    available_icu_beds = Column(Integer, default=5)
    total_general_beds = Column(Integer, default=50)
    available_general_beds = Column(Integer, default=15)
    trauma_bays = Column(Integer, default=10)
    blood_bank_status = Column(String(256), default="Full Stock")
    emergency_hotline = Column(String(64), nullable=False)
    status = Column(String(32), default="Operational")  # Operational, Surge Capacity, Diversion
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reservations = relationship("BedReservation", back_populates="hospital")
    beds = relationship("HospitalBed", back_populates="hospital")


class HospitalBed(Base):
    __tablename__ = "hospital_beds"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    bed_number = Column(String(32), nullable=False)
    bed_type = Column(String(32), default="ICU")  # ICU, Trauma, General, Emergency
    is_occupied = Column(Boolean, default=False)
    current_reservation_id = Column(String(32), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="beds")


class BedReservation(Base):
    __tablename__ = "hospital_bed_reservations"

    reservation_id = Column(String(32), primary_key=True, index=True, nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    incident_id = Column(String(32), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    dispatch_id = Column(String(32), nullable=True)
    patient_identifier = Column(String(64), nullable=False)
    bed_type = Column(String(32), default="ICU")
    reserved_by = Column(String(64), nullable=False)
    patient_handover_status = Column(String(32), default="Pending Arrival")  # Pending Arrival, Patient Admitted, Transferred, Released, Rejected
    status = Column(String(32), default="Pending")  # Pending, Accepted, Rejected, Completed
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    reserved_at = Column(DateTime, default=datetime.utcnow)
    handover_at = Column(DateTime, nullable=True)

    hospital = relationship("Hospital", back_populates="reservations")
    incident = relationship("Incident", back_populates="reservations")


class PatientHandoff(Base):
    __tablename__ = "patient_handoffs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reservation_id = Column(String(32), nullable=False, index=True)
    incident_id = Column(String(32), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    driver_id = Column(Integer, nullable=True)
    patient_condition = Column(String(128), default="Critical Stabilized")
    receiving_doctor = Column(String(128), nullable=False)
    handover_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient_role = Column(String(32), index=True, nullable=True)  # All, CONTROL_ROOM_OPERATOR, AMBULANCE_DRIVER, HOSPITAL_OPERATOR, CITIZEN
    recipient_id = Column(String(64), index=True, nullable=True)
    event_type = Column(String(64), nullable=False)  # INCIDENT_REPORTED, DISPATCH_ASSIGNED, DRIVER_ACCEPTED, PATIENT_ADMITTED, etc.
    title = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    incident_id = Column(String(32), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class V2XMeshNode(Base):
    __tablename__ = "v2x_mesh_nodes"

    node_id = Column(String(32), primary_key=True, index=True, nullable=False)
    node_type = Column(String(32), nullable=False)  # RSU, Ambulance, Police_Vehicle, Transit_Bus, Private_EV
    label = Column(String(128), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    firmware_version = Column(String(32), default="v2.5-vanet")
    tx_power_dbm = Column(Float, default=20.0)
    status = Column(String(32), default="Online")


class V2XRelayLog(Base):
    __tablename__ = "v2x_relay_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(32), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_hops = Column(Integer, default=3)
    hops_completed = Column(Integer, default=3)
    delivery_ratio = Column(Float, default=1.0)
    total_latency_ms = Column(Float, default=45.0)
    raw_payload_hex = Column(String(64), nullable=False)
    final_status = Column(String(32), default="DELIVERED")
    hop_details_json = Column(Text, default="[]")


class IncidentHistory(Base):
    __tablename__ = "incident_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(32), nullable=False, index=True)
    status_from = Column(String(32), nullable=True)
    status_to = Column(String(32), nullable=False)
    changed_by = Column(String(64), nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    target_entity = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), default="127.0.0.1")
