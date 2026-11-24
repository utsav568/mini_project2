import { Incident, Vehicle, Hospital, Dispatch, BedReservation, User, KPISummary } from './types';

export const API_BASE =
  typeof window !== 'undefined' && window.location.origin && !window.location.origin.includes('localhost:5173')
    ? window.location.origin
    : 'http://localhost:8000';

export const WS_BASE =
  typeof window !== 'undefined' && window.location.host
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/telemetry`
    : 'ws://localhost:8000/ws/telemetry';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('roadsos_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export async function apiLogin(username: string, password: string): Promise<{ access_token: string; user: User }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  localStorage.setItem('roadsos_token', data.access_token);
  localStorage.setItem('roadsos_user', JSON.stringify(data.user));
  return data;
}

export function apiLogout() {
  localStorage.removeItem('roadsos_token');
  localStorage.removeItem('roadsos_user');
}

export function getStoredUser(): User | null {
  const user = localStorage.getItem('roadsos_user');
  return user ? JSON.parse(user) : null;
}

// ---------------------------------------------------------------------------
// Incidents
// ---------------------------------------------------------------------------
export async function apiReportIncident(payload: {
  witness_statement: string;
  latitude: number;
  longitude: number;
  witness_name?: string;
  witness_phone?: string;
  category?: string;
  reported_casualties?: number;
  vehicles_count?: number;
  hazards?: string[];
  visual_tags?: string[];
}): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/incidents`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit emergency report');
  }
  return res.json();
}

export async function apiGetIncidents(params?: { status?: string; category?: string; search?: string }): Promise<Incident[]> {
  const url = new URL(`${API_BASE}/api/incidents`);
  if (params?.status) url.searchParams.append('status', params.status);
  if (params?.category) url.searchParams.append('category', params.category);
  if (params?.search) url.searchParams.append('search', params.search);

  const res = await fetch(url.toString());
  if (!res.ok) return [];
  return res.json();
}

export async function apiGetIncident(incidentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/incidents/${incidentId}`);
  if (!res.ok) throw new Error('Incident not found');
  return res.json();
}

export async function apiVerifyIncident(incidentId: string, status: string, reason?: string) {
  const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ status, verification_reason: reason }),
  });
  return res.json();
}

export async function apiUploadEvidence(incidentId: string, file: File, visualTags?: string[]) {
  const formData = new FormData();
  formData.append('file', file);
  if (visualTags) formData.append('visual_tags', JSON.stringify(visualTags));

  const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/evidence`, {
    method: 'POST',
    headers: getAuthHeader(),
    body: formData,
  });
  return res.json();
}

// ---------------------------------------------------------------------------
// Vehicles & Fleet
// ---------------------------------------------------------------------------
export async function apiGetFleet(): Promise<Vehicle[]> {
  const res = await fetch(`${API_BASE}/api/vehicles`);
  if (!res.ok) return [];
  return res.json();
}

export async function apiDispatchVehicle(incidentId: string, vehicleId: number, notes?: string) {
  const res = await fetch(`${API_BASE}/api/vehicles/dispatch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ incident_id: incidentId, vehicle_id: vehicleId, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Dispatch failed');
  }
  return res.json();
}

export async function apiGetDriverActiveDispatch(): Promise<{
  active: boolean;
  dispatch: Dispatch | null;
  incident: Incident | null;
  vehicle: Vehicle | null;
}> {
  const res = await fetch(`${API_BASE}/api/vehicles/driver/active-dispatch`, {
    headers: getAuthHeader(),
  });
  if (!res.ok) return { active: false, dispatch: null, incident: null, vehicle: null };
  return res.json();
}

export async function apiDriverAction(action: string, reason?: string, hospitalId?: number) {
  const res = await fetch(`${API_BASE}/api/vehicles/driver/action`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ action, reason, destination_hospital_id: hospitalId }),
  });
  return res.json();
}

export async function apiUpdateDriverGPS(lat: number, lon: number, speed?: number, heading?: number) {
  const res = await fetch(`${API_BASE}/api/vehicles/driver/gps`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ latitude: lat, longitude: lon, speed_kmh: speed, heading_deg: heading }),
  });
  return res.json();
}

// ---------------------------------------------------------------------------
// Hospitals & Bed Allocation
// ---------------------------------------------------------------------------
export async function apiGetHospitals(): Promise<Hospital[]> {
  const res = await fetch(`${API_BASE}/api/hospitals`);
  if (!res.ok) return [];
  return res.json();
}

export async function apiUpdateHospitalBeds(hospitalId: number, icuBeds: number, status?: string) {
  const res = await fetch(`${API_BASE}/api/hospitals/${hospitalId}/beds`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ available_icu_beds: icuBeds, status }),
  });
  return res.json();
}

export async function apiReserveBed(payload: {
  hospital_id: number;
  incident_id: string;
  patient_identifier: string;
  bed_type?: string;
  notes?: string;
  dispatch_id?: string;
}): Promise<BedReservation> {
  const res = await fetch(`${API_BASE}/api/hospitals/reserve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Bed reservation failed');
  }
  return res.json();
}

export async function apiReservationAction(reservationId: string, action: string, reason?: string) {
  const res = await fetch(`${API_BASE}/api/hospitals/reservation/${reservationId}/action`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ action, reason }),
  });
  return res.json();
}

export async function apiGetIncomingAmbulances(hospitalId: number) {
  const res = await fetch(`${API_BASE}/api/hospitals/${hospitalId}/incoming`);
  if (!res.ok) return [];
  return res.json();
}

export async function apiGetHospitalReservations(hospitalId: number) {
  const res = await fetch(`${API_BASE}/api/hospitals/${hospitalId}/reservations`);
  if (!res.ok) return [];
  return res.json();
}

// ---------------------------------------------------------------------------
// AI & Routing & Analytics
// ---------------------------------------------------------------------------
export async function apiAIAnalyze(text: string, visualTags?: string[]) {
  const res = await fetch(`${API_BASE}/api/ai/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, visual_tags: visualTags }),
  });
  return res.json();
}

export async function apiComputeRoute(srcLat: number, srcLon: number, destLat: number, destLon: number, vehicleType = 'ambulance') {
  const res = await fetch(`${API_BASE}/api/routing/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_lat: srcLat,
      source_lon: srcLon,
      dest_lat: destLat,
      dest_lon: destLon,
      vehicle_type: vehicleType,
    }),
  });
  return res.json();
}

export async function apiSimulateMesh(lat: number, lon: number, urgency: number, hops = 4) {
  const res = await fetch(`${API_BASE}/api/mesh/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ latitude: lat, longitude: lon, urgency_index: urgency, hops }),
  });
  return res.json();
}

export async function apiGetKPIs(): Promise<KPISummary> {
  const res = await fetch(`${API_BASE}/api/analytics/kpis`);
  if (!res.ok) {
    return {
      total_incidents: 0,
      active_emergencies: 0,
      critical_incidents: 0,
      available_vehicles: 0,
      dispatched_vehicles: 0,
      available_icu_beds: 0,
      total_icu_beds: 0,
      average_response_time_min: 0,
    };
  }
  return res.json();
}

export async function apiGetAnalyticsSummary() {
  const res = await fetch(`${API_BASE}/api/analytics/summary`);
  return res.json();
}

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------
export function connectTelemetryWebSocket(onEvent: (event: { type: string; data: any }) => void): WebSocket {
  const socket = new WebSocket(WS_BASE);
  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onEvent(parsed);
    } catch (e) {
      console.warn('Failed to parse WebSocket message:', e);
    }
  };
  socket.onclose = () => {
    console.log('Telemetry WebSocket closed. Reconnecting in 3s...');
    setTimeout(() => connectTelemetryWebSocket(onEvent), 3000);
  };
  return socket;
}
