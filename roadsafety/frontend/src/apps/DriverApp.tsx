import React, { useState, useEffect } from 'react';
import {
  Navigation, CheckCircle2, XCircle, AlertCircle, MapPin,
  Clock, Shield, User as UserIcon, LogOut, Radio, Play, Pause, ChevronRight
} from 'lucide-react';
import { EmergencyMap } from '../components/EmergencyMap';
import {
  apiLogin, apiLogout, getStoredUser, apiGetDriverActiveDispatch,
  apiDriverAction, apiUpdateDriverGPS, apiComputeRoute, connectTelemetryWebSocket
} from '../api';
import { Dispatch, Incident, Vehicle, User } from '../types';

export const DriverApp: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(getStoredUser());
  const [username, setUsername] = useState('medic');
  const [password, setPassword] = useState('medic123');
  const [loginError, setLoginError] = useState('');

  // Active Dispatch State
  const [activeDispatch, setActiveDispatch] = useState<Dispatch | null>(null);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);
  const [assignedVehicle, setAssignedVehicle] = useState<Vehicle | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Live Navigation & Route
  const [currentGps, setCurrentGps] = useState<[number, number]>([28.6315, 77.2167]);
  const [routeCoords, setRouteCoords] = useState<[number, number][]>([]);
  const [isSimulatingGps, setIsSimulatingGps] = useState(false);
  const [dutyStatus, setDutyStatus] = useState<'Available' | 'Busy' | 'Off Duty'>('Available');

  useEffect(() => {
    if (currentUser) {
      loadActiveDispatch();
      const ws = connectTelemetryWebSocket((event) => {
        if (event.type === 'DISPATCH_ASSIGNED' || event.type === 'DRIVER_STATUS_UPDATED') {
          loadActiveDispatch();
        }
      });
      return () => ws.close();
    }
  }, [currentUser]);

  // GPS Simulation Loop
  useEffect(() => {
    let interval: any = null;
    if (isSimulatingGps && routeCoords.length > 0) {
      let step = 0;
      interval = setInterval(() => {
        if (step < routeCoords.length) {
          const nextPt = routeCoords[step];
          setCurrentGps(nextPt);
          apiUpdateDriverGPS(nextPt[0], nextPt[1], 52.0, 45.0);
          step++;
        } else {
          setIsSimulatingGps(false);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isSimulatingGps, routeCoords]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await apiLogin(username, password);
      setCurrentUser(res.user);
    } catch (err: any) {
      setLoginError(err.message || 'Login failed');
    }
  };

  const loadActiveDispatch = async () => {
    setIsLoading(true);
    try {
      const res = await apiGetDriverActiveDispatch();
      if (res.active && res.dispatch) {
        setActiveDispatch(res.dispatch);
        setActiveIncident(res.incident);
        setAssignedVehicle(res.vehicle);

        if (res.incident) {
          // Compute route from current GPS to incident
          const route = await apiComputeRoute(
            currentGps[0], currentGps[1],
            res.incident.latitude, res.incident.longitude
          );
          if (route && route.path_coords) {
            setRouteCoords(route.path_coords);
          }
        }
      } else {
        setActiveDispatch(null);
        setActiveIncident(null);
      }
    } catch (err) {
      console.warn('Failed to load active dispatch');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (action: string, reason?: string) => {
    try {
      await apiDriverAction(action, reason);
      await loadActiveDispatch();
    } catch (err: any) {
      alert(err.message || `Failed to execute ${action}`);
    }
  };

  // ---------------- LOGIN SCREEN ----------------
  if (!currentUser) {
    return (
      <div className="max-w-md mx-auto min-h-screen bg-slate-950 p-6 flex flex-col justify-center items-center">
        <div className="w-full tactical-card p-6 space-y-4 border-cyan-500/30">
          <div className="text-center space-y-1">
            <div className="w-12 h-12 bg-cyan-950 border border-cyan-500/40 text-cyan-400 rounded-2xl mx-auto flex items-center justify-center font-bold text-xl shadow-lg shadow-cyan-950">
              🚑
            </div>
            <h1 className="font-black text-xl text-white">Driver CAD Terminal</h1>
            <p className="text-xs text-slate-400">Emergency Fleet Telematics PWA</p>
          </div>

          {loginError && (
            <div className="bg-red-950/80 border border-red-800 text-red-300 p-2.5 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 font-mono">DRIVER USERNAME</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 font-mono">PASSWORD</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-cyan-500 hover:bg-cyan-400 text-black font-black py-3 rounded-xl shadow-lg shadow-cyan-950 flex items-center justify-center gap-2 text-sm uppercase tracking-wider"
            >
              Sign In to Duty Shift
            </button>
          </form>

          <div className="text-[11px] text-slate-500 text-center border-t border-slate-900 pt-3">
            Demo Credentials: <code className="text-cyan-400 font-mono">medic / medic123</code>
          </div>
        </div>
      </div>
    );
  }

  // ---------------- ACTIVE DRIVER TERMINAL ----------------
  return (
    <div className="max-w-md mx-auto min-h-screen bg-slate-950 text-slate-100 flex flex-col border-x border-slate-900 pb-16">
      {/* Top Header */}
      <header className="bg-slate-900 border-b border-slate-800 p-4 sticky top-0 z-30 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-400 flex items-center justify-center font-bold text-sm">
            🚑
          </div>
          <div>
            <div className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>{assignedVehicle?.callsign || 'UNIT-ALS-101'}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">{currentUser.full_name}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Duty Status Selector */}
          <select
            value={dutyStatus}
            onChange={(e) => setDutyStatus(e.target.value as any)}
            className="bg-slate-800 border border-slate-700 text-xs rounded-lg px-2 py-1 text-emerald-400 font-bold focus:outline-none"
          >
            <option value="Available">🟢 On Duty</option>
            <option value="Busy">🟠 Busy</option>
            <option value="Off Duty">⚪ Off Duty</option>
          </select>

          <button
            onClick={() => {
              apiLogout();
              setCurrentUser(null);
            }}
            className="p-1.5 text-slate-400 hover:text-red-400 bg-slate-800 rounded-lg"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 space-y-4">
        {activeDispatch && activeIncident ? (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Active Dispatch Card */}
            <div className="tactical-card p-4 space-y-3 border-orange-500/30">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div>
                  <span className="text-[10px] text-orange-400 font-bold uppercase tracking-wider flex items-center gap-1">
                    <Radio className="w-3 h-3 text-orange-400 animate-pulse" /> ACTIVE DISPATCH
                  </span>
                  <h2 className="font-mono font-bold text-base text-white">{activeDispatch.dispatch_id}</h2>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 font-mono">INCIDENT</span>
                  <div className="font-mono text-xs text-cyan-400 font-bold">{activeIncident.incident_id}</div>
                </div>
              </div>

              {/* Incident Summary */}
              <div className="space-y-1">
                <div className="text-sm font-bold text-white flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-red-400" />
                  {activeIncident.category}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  {activeIncident.witness_statement}
                </p>
                <div className="text-xs text-cyan-400 flex items-center gap-1 pt-0.5">
                  <MapPin className="w-3.5 h-3.5" />
                  <b>{activeIncident.landmark}</b>
                </div>
              </div>

              {/* Status Indicator */}
              <div className="flex items-center justify-between text-xs bg-slate-900 p-2 rounded-lg font-mono">
                <span className="text-slate-400">DISPATCH STATUS:</span>
                <span className="text-orange-400 font-bold uppercase">{activeDispatch.status}</span>
              </div>
            </div>

            {/* Turn-by-Turn Interactive Map */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
                <span>TACTICAL GPS ROUTE</span>
                <button
                  onClick={() => setIsSimulatingGps(!isSimulatingGps)}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-sans font-bold transition ${
                    isSimulatingGps ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-cyan-950 text-cyan-400 border border-cyan-800'
                  }`}
                >
                  {isSimulatingGps ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                  {isSimulatingGps ? 'Pause GPS Sim' : 'Simulate GPS Driving'}
                </button>
              </div>

              <EmergencyMap
                center={currentGps}
                selectedLocation={currentGps}
                routeCoords={routeCoords}
                incidents={[activeIncident]}
                height="240px"
              />
            </div>

            {/* Workflow Action Buttons */}
            <div className="space-y-2 pt-2">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Driver Operational Steps</div>

              {activeDispatch.status === 'En Route' && (
                <button
                  onClick={() => handleAction('on_scene')}
                  className="w-full bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-black py-3.5 rounded-xl text-sm shadow-lg shadow-orange-950 flex items-center justify-center gap-2"
                >
                  <MapPin className="w-4 h-4" />
                  MARK ARRIVED ON SCENE
                </button>
              )}

              {activeDispatch.status === 'On Scene' && (
                <button
                  onClick={() => handleAction('transporting', undefined, 1)}
                  className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-black py-3.5 rounded-xl text-sm shadow-lg shadow-blue-950 flex items-center justify-center gap-2"
                >
                  <Navigation className="w-4 h-4" />
                  PATIENT ONBOARD → NAVIGATE TO HOSPITAL
                </button>
              )}

              {activeDispatch.status === 'Transporting Patient' && (
                <button
                  onClick={() => handleAction('at_hospital')}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-black py-3.5 rounded-xl text-sm shadow-lg shadow-purple-950 flex items-center justify-center gap-2"
                >
                  <Shield className="w-4 h-4" />
                  ARRIVED AT TRAUMA HOSPITAL
                </button>
              )}

              {activeDispatch.status === 'At Hospital' && (
                <button
                  onClick={() => handleAction('complete')}
                  className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black py-3.5 rounded-xl text-sm shadow-lg shadow-emerald-950 flex items-center justify-center gap-2"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  COMPLETE HANDOVER & CLOSE DISPATCH
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="tactical-card p-8 text-center space-y-4 my-8">
            <div className="w-16 h-16 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center justify-center mx-auto text-2xl font-bold">
              ✓
            </div>
            <div>
              <h2 className="font-bold text-lg text-white">Standby & Ready for Dispatch</h2>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                No active dispatches assigned to this unit. Maintain GPS telemetry and monitor Central CAD queue.
              </p>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-xs font-mono text-slate-400 text-left space-y-1">
              <div>Assigned Unit: <span className="text-white font-bold">{assignedVehicle?.callsign || 'AMB-101'}</span></div>
              <div>Station: <span className="text-cyan-400">Central Fire HQ (Connaught Hub)</span></div>
              <div>Fuel Status: <span className="text-emerald-400">95% Full</span></div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
