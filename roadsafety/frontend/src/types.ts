export interface Incident {
  id?: number;
  incident_id: string;
  witness_name: string;
  witness_phone: string;
  witness_statement: string;
  category: string;
  severity: string;
  latitude: number;
  longitude: number;
  grid_node?: number;
  landmark: string;
  status: string; // Reported, Under Verification, AI Analyzed, Verified, Response Dispatched, En Route, On Scene, Rescue in Progress, Resolved, Cancelled, Rejected
  urgency_index: number;
  golden_hour_sla_min: number;
  ai_analysis_reasoning?: string;
  vehicles_involved: number;
  casualties_count: number;
  hazards_detected?: string;
  recommended_units?: string;
  reported_by?: string;
  verified_by?: string;
  verification_reason?: string;
  created_at: string;
  updated_at?: string;
}

export interface Vehicle {
  id: number;
  callsign: string;
  vehicle_type: string;
  label: string;
  station_base: string;
  current_lat: number;
  current_lon: number;
  status: string; // Available, Assigned, En Route, On Scene, Transporting Patient, At Hospital, Out of Service
  crew_lead: string;
  fuel_level_pct: number;
  active_incident_id?: string;
  active_driver_id?: number;
}

export interface Hospital {
  id: number;
  name: string;
  category: string;
  address: string;
  latitude: number;
  longitude: number;
  total_icu_beds: number;
  available_icu_beds: number;
  total_general_beds: number;
  available_general_beds: number;
  trauma_bays: number;
  blood_bank_status: string;
  emergency_hotline: string;
  status: string; // Operational, Surge Capacity, Diversion
}

export interface Dispatch {
  id?: number;
  dispatch_id: string;
  incident_id: string;
  vehicle_id: number;
  driver_id?: number;
  assigned_by: string;
  status: string; // Active, Accepted, Rejected, En Route, On Scene, Transporting Patient, At Hospital, Completed, Cancelled
  route_time_min: number;
  route_distance_km: number;
  destination_hospital_id?: number;
  eta_min: number;
  dispatch_notes?: string;
  assigned_at: string;
  en_route_at?: string;
  on_scene_at?: string;
  at_hospital_at?: string;
  completed_at?: string;
}

export interface BedReservation {
  id?: number;
  reservation_id: string;
  hospital_id: number;
  incident_id: string;
  dispatch_id?: string;
  patient_identifier: string;
  bed_type: string;
  reserved_by: string;
  patient_handover_status: string; // Pending Arrival, Patient Admitted, Transferred, Released, Rejected
  status: string; // Pending, Accepted, Rejected, Completed
  notes?: string;
  reserved_at: string;
}

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: string;
  badge_number?: string;
  phone?: string;
  hospital_id?: number;
  vehicle_id?: number;
}

export interface KPISummary {
  total_incidents: number;
  active_emergencies: number;
  critical_incidents: number;
  available_vehicles: number;
  dispatched_vehicles: number;
  available_icu_beds: number;
  total_icu_beds: number;
  average_response_time_min: number;
}
