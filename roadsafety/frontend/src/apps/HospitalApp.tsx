import React, { useState, useEffect } from 'react';
import {
  Building2, Bed, AlertCircle, CheckCircle2, XCircle, Clock,
  PhoneCall, Users, ShieldAlert, LogOut, ArrowRight, Activity, RefreshCw
} from 'lucide-react';
import {
  apiLogin, apiLogout, getStoredUser, apiGetHospitals,
  apiUpdateHospitalBeds, apiGetIncomingAmbulances, apiGetHospitalReservations,
  apiReservationAction, connectTelemetryWebSocket
} from '../api';
import { Hospital, BedReservation, User } from '../types';

export const HospitalApp: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(getStoredUser());
  const [username, setUsername] = useState('aiims_admin');
  const [password, setPassword] = useState('hospital123');
  const [loginError, setLoginError] = useState('');

  // Hospital State
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [selectedHospitalId, setSelectedHospitalId] = useState<number>(1);
  const [incomingAmbulances, setIncomingAmbulances] = useState<any[]>([]);
  const [reservations, setReservations] = useState<BedReservation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (currentUser) {
      loadHospitalData();
      const ws = connectTelemetryWebSocket((event) => {
        if (
          event.type === 'BED_RESERVED' ||
          event.type === 'RESERVATION_UPDATED' ||
          event.type === 'DISPATCH_ASSIGNED' ||
          event.type === 'DRIVER_STATUS_UPDATED'
        ) {
          loadHospitalData();
        }
      });
      return () => ws.close();
    }
  }, [currentUser, selectedHospitalId]);

  const loadHospitalData = async () => {
    setIsLoading(true);
    try {
      const allHospitals = await apiGetHospitals();
      setHospitals(allHospitals);
      const hid = currentUser?.hospital_id || selectedHospitalId;
      setSelectedHospitalId(hid);

      const incoming = await apiGetIncomingAmbulances(hid);
      setIncomingAmbulances(incoming);

      const resList = await apiGetHospitalReservations(hid);
      setReservations(resList);
    } catch (err) {
      console.warn('Failed to load hospital data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await apiLogin(username, password);
      setCurrentUser(res.user);
      if (res.user.hospital_id) {
        setSelectedHospitalId(res.user.hospital_id);
      }
    } catch (err: any) {
      setLoginError(err.message || 'Login failed');
    }
  };

  const handleUpdateBeds = async (newCount: number) => {
    try {
      await apiUpdateHospitalBeds(selectedHospitalId, newCount);
      loadHospitalData();
    } catch (err) {
      alert('Failed to update bed capacity');
    }
  };

  const handleUpdateStatus = async (newStatus: string) => {
    const curHosp = hospitals.find((h) => h.id === selectedHospitalId);
    if (!curHosp) return;
    try {
      await apiUpdateHospitalBeds(selectedHospitalId, curHosp.available_icu_beds, newStatus);
      loadHospitalData();
    } catch (err) {
      alert('Failed to update operational status');
    }
  };

  const handleReservationAction = async (resId: string, action: string) => {
    try {
      await apiReservationAction(resId, action);
      loadHospitalData();
    } catch (err: any) {
      alert(err.message || `Failed to execute ${action}`);
    }
  };

  const currentHospital = hospitals.find((h) => h.id === selectedHospitalId);

  // ---------------- LOGIN SCREEN ----------------
  if (!currentUser) {
    return (
      <div className="max-w-md mx-auto min-h-screen bg-slate-950 p-6 flex flex-col justify-center items-center">
        <div className="w-full tactical-card p-6 space-y-4 border-blue-500/30">
          <div className="text-center space-y-1">
            <div className="w-12 h-12 bg-blue-950 border border-blue-500/40 text-blue-400 rounded-2xl mx-auto flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-950">
              🏥
            </div>
            <h1 className="font-black text-xl text-white">Trauma Centre Portal</h1>
            <p className="text-xs text-slate-400">Hospital Emergency Resuscitation Console</p>
          </div>

          {loginError && (
            <div className="bg-red-950/80 border border-red-800 text-red-300 p-2.5 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 font-mono">OPERATOR USERNAME</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 font-mono">PASSWORD</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-blue-500 hover:bg-blue-400 text-black font-black py-3 rounded-xl shadow-lg shadow-blue-950 flex items-center justify-center gap-2 text-sm uppercase tracking-wider"
            >
              Sign In to Hospital Portal
            </button>
          </form>

          <div className="text-[11px] text-slate-500 text-center border-t border-slate-900 pt-3">
            Demo Credentials: <code className="text-blue-400 font-mono">aiims_admin / hospital123</code>
          </div>
        </div>
      </div>
    );
  }

  // ---------------- ACTIVE HOSPITAL DASHBOARD ----------------
  return (
    <div className="max-w-4xl mx-auto min-h-screen bg-slate-950 text-slate-100 flex flex-col p-4 md:p-6 space-y-6">
      {/* Header */}
      <header className="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-800 text-blue-400 flex items-center justify-center font-bold text-lg">
            🏥
          </div>
          <div>
            <h1 className="font-bold text-base text-white flex items-center gap-2">
              {currentHospital?.name || 'AIIMS Apex Trauma Centre'}
              <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                currentHospital?.status === 'Operational' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
              }`}>
                {currentHospital?.status || 'Operational'}
              </span>
            </h1>
            <p className="text-xs text-slate-400">{currentHospital?.address}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          {/* Hospital Switcher */}
          <select
            value={selectedHospitalId}
            onChange={(e) => setSelectedHospitalId(Number(e.target.value))}
            className="bg-slate-800 border border-slate-700 text-xs text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none"
          >
            {hospitals.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              apiLogout();
              setCurrentUser(null);
            }}
            className="p-2 text-slate-400 hover:text-red-400 bg-slate-800 rounded-lg text-xs flex items-center gap-1"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="tactical-card p-4 space-y-1 border-blue-500/20">
          <div className="flex items-center justify-between text-xs text-blue-400 font-mono">
            <span>AVAILABLE ICU BEDS</span>
            <Bed className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">
            {currentHospital?.available_icu_beds || 0}
            <span className="text-xs font-normal text-slate-400"> / {currentHospital?.total_icu_beds || 0}</span>
          </div>
          <div className="flex items-center gap-1.5 pt-1">
            <button
              onClick={() => handleUpdateBeds(Math.max(0, (currentHospital?.available_icu_beds || 1) - 1))}
              className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-xs rounded text-slate-300 font-bold"
            >- 1</button>
            <button
              onClick={() => handleUpdateBeds(Math.min(currentHospital?.total_icu_beds || 20, (currentHospital?.available_icu_beds || 0) + 1))}
              className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-xs rounded text-slate-300 font-bold"
            >+ 1</button>
          </div>
        </div>

        <div className="tactical-card p-4 space-y-1 border-emerald-500/20">
          <div className="flex items-center justify-between text-xs text-emerald-400 font-mono">
            <span>GENERAL EMERGENCY BEDS</span>
            <Building2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">
            {currentHospital?.available_general_beds || 0}
            <span className="text-xs font-normal text-slate-400"> / {currentHospital?.total_general_beds || 0}</span>
          </div>
          <div className="text-[11px] text-emerald-400 pt-1 font-mono">
            Trauma Bays: {currentHospital?.trauma_bays || 10}
          </div>
        </div>

        <div className="tactical-card p-4 space-y-1 border-amber-500/20">
          <div className="flex items-center justify-between text-xs text-amber-400 font-mono">
            <span>INCOMING AMBULANCES</span>
            <Activity className="w-4 h-4 text-amber-400 animate-pulse" />
          </div>
          <div className="text-2xl font-black text-amber-400 font-mono">
            {incomingAmbulances.length}
          </div>
          <div className="text-[11px] text-slate-400 font-mono">En route with ETA &lt; 15m</div>
        </div>

        <div className="tactical-card p-4 space-y-1 border-purple-500/20">
          <div className="flex items-center justify-between text-xs text-purple-400 font-mono">
            <span>ACTIVE RESERVATIONS</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-black text-purple-400 font-mono">
            {reservations.filter((r) => r.status === 'Pending' || r.status === 'Accepted').length}
          </div>
          <div className="text-[11px] text-slate-400 font-mono">Pre-hospital triage</div>
        </div>
      </div>

      {/* Main Grid: Incoming Ambulances & Bed Reservation Queue */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Incoming Ambulances Queue */}
        <div className="tactical-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h2 className="font-bold text-sm text-white flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping"></span>
              Incoming Emergency Inbound Units
            </h2>
            <span className="text-xs font-mono text-slate-400">{incomingAmbulances.length} Units</span>
          </div>

          <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
            {incomingAmbulances.length > 0 ? (
              incomingAmbulances.map(({ dispatch, incident }) => (
                <div key={dispatch.dispatch_id} className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white font-mono text-sm">{dispatch.dispatch_id}</span>
                    <span className="bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded font-mono font-bold">
                      ETA ~{dispatch.eta_min.toFixed(0)} min
                    </span>
                  </div>
                  {incident && (
                    <div className="space-y-1 text-slate-300">
                      <div>Accident: <b>{incident.category}</b> ({incident.landmark})</div>
                      <div className="text-[11px] text-red-400">Severity: {incident.severity} | Casualties: {incident.casualties_count}</div>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-2 font-mono">
                    <span>STATUS: {dispatch.status}</span>
                    <span className="text-cyan-400">Distance: {dispatch.route_distance_km} km</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-500 space-y-1">
                <Clock className="w-8 h-8 mx-auto text-slate-600" />
                <p className="text-xs">No ambulances currently en route to this facility.</p>
              </div>
            )}
          </div>
        </div>

        {/* Bed Reservation Management */}
        <div className="tactical-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h2 className="font-bold text-sm text-white flex items-center gap-2">
              <Bed className="w-4 h-4 text-cyan-400" />
              Bed Reservation & Admission Protocol
            </h2>
            <button onClick={loadHospitalData} className="text-slate-400 hover:text-white">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
            {reservations.length > 0 ? (
              reservations.map((r) => (
                <div key={r.reservation_id} className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-slate-400 text-[10px]">PATIENT ID</span>
                      <div className="font-bold text-white font-mono">{r.patient_identifier}</div>
                    </div>
                    <span className={`px-2 py-0.5 rounded font-mono font-bold text-[11px] ${
                      r.patient_handover_status === 'Patient Admitted' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-blue-950 text-blue-400 border border-blue-800'
                    }`}>
                      {r.patient_handover_status}
                    </span>
                  </div>

                  <div className="text-slate-300 text-[11px]">
                    Reserved by: <span className="text-white font-medium">{r.reserved_by}</span> | Bed: <span className="text-cyan-400 font-mono">{r.bed_type}</span>
                  </div>

                  {r.patient_handover_status === 'Pending Arrival' && (
                    <div className="flex items-center gap-2 pt-1 border-t border-slate-800/80">
                      <button
                        onClick={() => handleReservationAction(r.reservation_id, 'admit')}
                        className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-black font-bold py-1.5 rounded-lg text-xs flex items-center justify-center gap-1"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Admission
                      </button>
                      <button
                        onClick={() => handleReservationAction(r.reservation_id, 'reject')}
                        className="px-3 bg-red-950 hover:bg-red-900 border border-red-800 text-red-300 font-bold py-1.5 rounded-lg text-xs"
                      >
                        Divert
                      </button>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-500 space-y-1">
                <Bed className="w-8 h-8 mx-auto text-slate-600" />
                <p className="text-xs">No active bed reservation requests.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
