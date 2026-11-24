import React, { useState, useEffect } from 'react';
import { PublicApp } from './apps/PublicApp';
import { DriverApp } from './apps/DriverApp';
import { HospitalApp } from './apps/HospitalApp';
import { AICopilotApp } from './apps/AICopilotApp';
import { ShieldAlert, Ambulance, Building2, Monitor, Radio, ExternalLink, Brain } from 'lucide-react';
import { API_BASE } from './api';

export const App: React.FC = () => {
  const [activeApp, setActiveApp] = useState<'public' | 'ai' | 'driver' | 'hospital'>('public');
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      setBackendHealthy(res.ok);
    } catch (e) {
      setBackendHealthy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans">
      {/* Ecosystem Global Navigation Bar */}
      <nav className="bg-slate-900/95 border-b border-slate-800 text-xs px-4 py-2 sticky top-0 z-50 backdrop-blur flex flex-wrap items-center justify-between gap-2 shadow-lg">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-md shadow-cyan-950">
            GN
          </div>
          <span className="font-bold text-white tracking-wide">
            GuardianNodes <span className="text-cyan-400 font-mono">RoadSoS</span>
          </span>
          <span className="hidden sm:inline-block text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
            ECOSYSTEM v2.5
          </span>
        </div>

        {/* Multi-App Switcher Buttons */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveApp('public')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeApp === 'public'
                ? 'bg-red-600 text-white shadow-md shadow-red-950'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Public SOS</span>
          </button>

          <button
            onClick={() => setActiveApp('ai')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeApp === 'ai'
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-950'
                : 'text-slate-400 hover:text-purple-300'
            }`}
          >
            <Brain className="w-3.5 h-3.5 text-purple-400" />
            <span>AI Copilot</span>
          </button>

          <button
            onClick={() => setActiveApp('driver')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeApp === 'driver'
                ? 'bg-cyan-500 text-black shadow-md shadow-cyan-950'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Ambulance className="w-3.5 h-3.5" />
            <span>Driver PWA</span>
          </button>

          <button
            onClick={() => setActiveApp('hospital')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeApp === 'hospital'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-950'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Hospital Portal</span>
          </button>

          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-amber-400 hover:bg-slate-800 transition"
            title="Open Streamlit CAD Control Room"
          >
            <Monitor className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Control Room</span>
            <ExternalLink className="w-3 h-3 text-slate-500" />
          </a>
        </div>

        {/* Live API Health Badge */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            <span className={`w-2 h-2 rounded-full ${backendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`}></span>
            <span className={backendHealthy ? 'text-emerald-400' : 'text-red-400'}>
              {backendHealthy ? 'FastAPI 8000 Online' : 'Connecting API...'}
            </span>
          </div>
        </div>
      </nav>

      {/* Render Selected App Component */}
      <div className="flex-1">
        {activeApp === 'public' && <PublicApp />}
        {activeApp === 'ai' && <AICopilotApp />}
        {activeApp === 'driver' && <DriverApp />}
        {activeApp === 'hospital' && <HospitalApp />}
      </div>
    </div>
  );
};
export default App;
