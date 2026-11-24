import React, { useState, useEffect } from 'react';
import {
  AlertTriangle, PhoneCall, ShieldAlert, MapPin, Send,
  Camera, CheckCircle2, Navigation, Clock, Info, Globe, ChevronRight, Activity
} from 'lucide-react';
import { EmergencyMap } from '../components/EmergencyMap';
import { apiReportIncident, apiGetIncidents } from '../api';
import { Incident } from '../types';

export const PublicApp: React.FC = () => {
  const [lang, setLang] = useState<'en' | 'hi'>('en');
  const [activeTab, setActiveTab] = useState<'home' | 'report' | 'track' | 'contacts'>('home');

  // Form State
  const [witnessStatement, setWitnessStatement] = useState('');
  const [category, setCategory] = useState('Road Collision');
  const [vehiclesCount, setVehiclesCount] = useState(2);
  const [casualtiesCount, setCasualtiesCount] = useState(1);
  const [witnessName, setWitnessName] = useState('');
  const [witnessPhone, setWitnessPhone] = useState('');
  const [location, setLocation] = useState<[number, number]>([28.5672, 77.2100]); // Default AIIMS
  const [isLocating, setIsLocating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionSuccess, setSubmissionSuccess] = useState<Incident | null>(null);

  // Tracking State
  const [trackIncidentId, setTrackIncidentId] = useState('');
  const [trackedIncident, setTrackedIncident] = useState<Incident | null>(null);
  const [recentReports, setRecentReports] = useState<Incident[]>([]);

  // Translations
  const t = {
    en: {
      sos: 'EMERGENCY SOS',
      sosSub: 'Tap for immediate GPS dispatch',
      reportAccident: 'Report Road Accident',
      trackIncident: 'Track Incident Status',
      contacts: 'Emergency Contacts',
      location: 'Accident Location',
      gpsDetect: 'Auto-Detect Current GPS',
      category: 'Accident Category',
      description: 'Accident Description',
      descPlaceholder: 'Describe the collision, trapped persons, vehicle types, fire...',
      vehicles: 'Vehicles Involved',
      casualties: 'Injured Persons',
      name: 'Your Name (Optional)',
      phone: 'Your Mobile Number',
      submit: 'SUBMIT EMERGENCY DISPATCH REPORT',
      submitting: 'Processing AI Triage & Submitting...',
      quickTags: ['Trapped Passengers', 'Vehicle on Fire', 'Highway Pileup', 'Fuel Leak', 'Head-on Crash'],
      statusReported: 'Reported',
      statusVerified: 'Verified',
      statusDispatched: 'Response Dispatched',
      statusRescue: 'Rescue in Progress',
      statusResolved: 'Resolved',
    },
    hi: {
      sos: 'आपातकालीन एसओएस',
      sosSub: 'तत्काल जीपीएस सहायता के लिए दबाएं',
      reportAccident: 'सड़क दुर्घटना रिपोर्ट करें',
      trackIncident: 'दुर्घटना स्थिति ट्रैक करें',
      contacts: 'आपातकालीन नंबर',
      location: 'दुर्घटना स्थल',
      gpsDetect: 'वर्तमान जीपीएस स्थान खोजें',
      category: 'दुर्घटना की श्रेणी',
      description: 'दुर्घटना का विवरण',
      descPlaceholder: 'दुर्घटना, घायल व्यक्ति, वाहनों के प्रकार या आग का विवरण दें...',
      vehicles: 'शामिल वाहन',
      casualties: 'घायल व्यक्तियों की संख्या',
      name: 'आपका नाम (वैकल्पिक)',
      phone: 'आपका मोबाइल नंबर',
      submit: 'आपातकालीन रिपोर्ट दर्ज करें',
      submitting: 'एआई विश्लेषण एवं सबमिट हो रहा है...',
      quickTags: ['फंसे हुए यात्री', 'वाहन में आग', 'राजमार्ग पर दुर्घटना', 'ईंधन रिसाव', 'आमने-सामने टक्कर'],
      statusReported: 'दर्ज हुई',
      statusVerified: 'सत्यापित',
      statusDispatched: 'वाहन रवाना',
      statusRescue: 'बचाव कार्य जारी',
      statusResolved: 'समाधान संपन्न',
    }
  }[lang];

  useEffect(() => {
    loadRecentReports();
  }, []);

  const loadRecentReports = async () => {
    try {
      const data = await apiGetIncidents({ limit: 5 as any });
      setRecentReports(data.slice(0, 4));
    } catch (e) {
      console.warn('Failed to load recent reports');
    }
  };

  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation([pos.coords.latitude, pos.coords.longitude]);
        setIsLocating(false);
      },
      () => {
        setIsLocating(false);
        alert('Could not access GPS. Please pin your location on the map.');
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleOneTouchSOS = async () => {
    if (!confirm(lang === 'hi' ? 'क्या आप तुरंत आपातकालीन एम्बुलेंस व पुलिस टीम बुलाना चाहते हैं?' : 'Dispatch immediate emergency ambulance and first responder team to your current location?')) {
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await apiReportIncident({
        witness_statement: 'CRITICAL ONE-TOUCH SOS: Citizen triggered immediate emergency dispatch button via mobile interface.',
        latitude: location[0],
        longitude: location[1],
        witness_name: 'Emergency SOS Citizen',
        category: 'Critical Medical Trauma',
        reported_casualties: 1,
        vehicles_count: 1,
      });
      setSubmissionSuccess(result);
      setTrackedIncident(result);
      setActiveTab('track');
    } catch (err: any) {
      alert(err.message || 'Error triggering SOS dispatch');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!witnessStatement.trim()) {
      alert('Please enter accident description.');
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await apiReportIncident({
        witness_statement: witnessStatement,
        latitude: location[0],
        longitude: location[1],
        witness_name: witnessName || 'Citizen Reporter',
        witness_phone: witnessPhone || 'N/A',
        category,
        reported_casualties: casualtiesCount,
        vehicles_count: vehiclesCount,
      });
      setSubmissionSuccess(result);
      setTrackedIncident(result);
      setActiveTab('track');
      setWitnessStatement('');
      loadRecentReports();
    } catch (err: any) {
      alert(err.message || 'Error submitting accident report');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSearchTracking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackIncidentId.trim()) return;
    try {
      const all = await apiGetIncidents({ search: trackIncidentId.trim() });
      if (all.length > 0) {
        setTrackedIncident(all[0]);
      } else {
        alert('Incident ID not found.');
      }
    } catch (err) {
      alert('Failed to find incident.');
    }
  };

  return (
    <div className="max-w-md mx-auto min-h-screen bg-slate-950 text-slate-100 flex flex-col pb-20 shadow-2xl border-x border-slate-900">
      {/* Top Header */}
      <header className="bg-slate-900/90 border-b border-slate-800 p-4 sticky top-0 z-30 backdrop-blur flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-red-600 to-orange-500 flex items-center justify-center text-white shadow-lg shadow-red-900/40 font-bold">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-black text-base tracking-tight text-white flex items-center gap-1.5">
              RoadSoS <span className="text-[10px] bg-red-950 text-red-400 border border-red-800 px-1.5 py-0.5 rounded font-mono">DELHI NCR</span>
            </h1>
            <p className="text-[11px] text-slate-400">Public Citizen Emergency Response</p>
          </div>
        </div>

        {/* Language Switcher */}
        <button
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
          className="flex items-center gap-1 text-xs bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 px-2.5 py-1.5 rounded-lg transition"
        >
          <Globe className="w-3.5 h-3.5" />
          <span className="font-bold">{lang === 'en' ? 'हिंदी' : 'English'}</span>
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 space-y-4">
        {activeTab === 'home' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Live Location Alert Bar */}
            <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-slate-300">
                <MapPin className="w-4 h-4 text-cyan-400" />
                <span>GPS: <b>{location[0].toFixed(4)}, {location[1].toFixed(4)}</b></span>
              </div>
              <button
                onClick={handleGetCurrentLocation}
                className="text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1 text-[11px]"
              >
                {isLocating ? 'Locating...' : 'Update'}
              </button>
            </div>

            {/* Giant Emergency SOS Button */}
            <div className="tactical-card p-6 flex flex-col items-center justify-center text-center space-y-4 border-red-500/20">
              <div className="text-center">
                <h2 className="text-sm font-semibold text-red-400 tracking-wider uppercase">{t.sosSub}</h2>
              </div>
              <button
                onClick={handleOneTouchSOS}
                disabled={isSubmitting}
                className="w-44 h-44 rounded-full bg-gradient-to-tr from-red-600 via-red-500 to-orange-500 text-white font-black text-2xl tracking-wider flex flex-col items-center justify-center shadow-2xl shadow-red-600/50 sos-button-pulse active:scale-95 transition hover:brightness-110"
              >
                <AlertTriangle className="w-12 h-12 mb-1" />
                <span>{t.sos}</span>
                <span className="text-[10px] font-normal tracking-normal opacity-90 mt-0.5">PRESS & HOLD</span>
              </button>
              <p className="text-xs text-slate-400 max-w-xs">
                {lang === 'hi'
                  ? 'दबाते ही नजदीकी एम्बुलेंस व कंट्रोल रूम को सूचना मिल जाएगी।'
                  : 'Instantly alerts Delhi NCR Emergency Dispatch & transmits live GPS coordinates.'}
              </p>
            </div>

            {/* Action Cards */}
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setActiveTab('report')}
                className="tactical-card p-4 text-left hover:border-cyan-500/40 transition group"
              >
                <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 flex items-center justify-center mb-2 border border-cyan-800/50 group-hover:scale-105 transition">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-white">{t.reportAccident}</h3>
                <p className="text-[11px] text-slate-400 mt-1">Multi-vehicle, fire, injuries, photo</p>
              </button>

              <button
                onClick={() => setActiveTab('track')}
                className="tactical-card p-4 text-left hover:border-cyan-500/40 transition group"
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-950 text-emerald-400 flex items-center justify-center mb-2 border border-emerald-800/50 group-hover:scale-105 transition">
                  <Activity className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-white">{t.trackIncident}</h3>
                <p className="text-[11px] text-slate-400 mt-1">Live status, ambulance ETA</p>
              </button>
            </div>

            {/* Quick Emergency Hotlines */}
            <div className="tactical-card p-4 space-y-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Direct Emergency Call</span>
                <PhoneCall className="w-3.5 h-3.5 text-red-400" />
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <a href="tel:112" className="bg-red-950/60 hover:bg-red-900 border border-red-800/60 p-2.5 rounded-lg font-bold text-red-300">
                  <div className="text-[10px] text-slate-400">National</div>112 ERSS
                </a>
                <a href="tel:102" className="bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/60 p-2.5 rounded-lg font-bold text-cyan-300">
                  <div className="text-[10px] text-slate-400">Ambulance</div>102 CATS
                </a>
                <a href="tel:101" className="bg-orange-950/60 hover:bg-orange-900 border border-orange-800/60 p-2.5 rounded-lg font-bold text-orange-300">
                  <div className="text-[10px] text-slate-400">Fire Tender</div>101 FIRE
                </a>
              </div>
            </div>

            {/* Recent Reports in City */}
            {recentReports.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Recent Local Incidents</span>
                {recentReports.map((r) => (
                  <div
                    key={r.incident_id}
                    onClick={() => {
                      setTrackedIncident(r);
                      setActiveTab('track');
                    }}
                    className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 p-3 rounded-xl flex items-center justify-between text-xs cursor-pointer"
                  >
                    <div>
                      <div className="font-bold text-white flex items-center gap-1.5">
                        <span>💥 {r.incident_id}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                          r.status === 'Resolved' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
                        }`}>
                          {r.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-[220px]">{r.landmark || r.category}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ----------------- REPORT ACCIDENT TAB ----------------- */}
        {activeTab === 'report' && (
          <form onSubmit={handleSubmitReport} className="space-y-4 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h2 className="font-bold text-base text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                {t.reportAccident}
              </h2>
              <button
                type="button"
                onClick={() => setActiveTab('home')}
                className="text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
            </div>

            {/* Step 1: Location & Interactive Map Picker */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-300 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                  {t.location}
                </label>
                <button
                  type="button"
                  onClick={handleGetCurrentLocation}
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                >
                  <Navigation className="w-3 h-3" />
                  {isLocating ? 'Locating...' : t.gpsDetect}
                </button>
              </div>

              <EmergencyMap
                center={location}
                zoom={14}
                pickable={true}
                selectedLocation={location}
                onLocationSelect={(lat, lon) => setLocation([lat, lon])}
                height="220px"
              />
              <p className="text-[11px] text-slate-400 text-center font-mono">
                GPS: {location[0].toFixed(5)}, {location[1].toFixed(5)}
              </p>
            </div>

            {/* Step 2: Category Selection */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-300">{t.category}</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="Road Collision">🚗 Road Collision (2+ Vehicles)</option>
                <option value="Vehicle Fire">🔥 Vehicle Fire / Explosion</option>
                <option value="Critical Medical Trauma">🚑 Critical Medical Trauma</option>
                <option value="Vehicle Rollover">🔄 Vehicle Rollover</option>
                <option value="Hazardous Material Leak">☣️ Chemical / Fuel Leakage</option>
                <option value="Minor Collision">🚙 Minor Fender Bender</option>
              </select>
            </div>

            {/* Step 3: Description with Quick Tags */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-300">{t.description}</label>
              <textarea
                required
                rows={3}
                value={witnessStatement}
                onChange={(e) => setWitnessStatement(e.target.value)}
                placeholder={t.descPlaceholder}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
              {/* Quick Tags */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {t.quickTags.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setWitnessStatement((prev) => (prev ? `${prev}, ${tag}` : tag))}
                    className="text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-2 py-1 rounded-md transition"
                  >
                    + {tag}
                  </button>
                ))}
              </div>
            </div>

            {/* Step 4: Casualties & Vehicle Count */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-300">{t.vehicles}</label>
                <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl p-1.5">
                  <button
                    type="button"
                    onClick={() => setVehiclesCount(Math.max(1, vehiclesCount - 1))}
                    className="w-8 h-8 rounded-lg bg-slate-800 text-white font-bold"
                  >-</button>
                  <span className="flex-1 text-center font-bold text-sm">{vehiclesCount}</span>
                  <button
                    type="button"
                    onClick={() => setVehiclesCount(vehiclesCount + 1)}
                    className="w-8 h-8 rounded-lg bg-slate-800 text-white font-bold"
                  >+</button>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-red-300">{t.casualties}</label>
                <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl p-1.5">
                  <button
                    type="button"
                    onClick={() => setCasualtiesCount(Math.max(0, casualtiesCount - 1))}
                    className="w-8 h-8 rounded-lg bg-slate-800 text-white font-bold"
                  >-</button>
                  <span className="flex-1 text-center font-bold text-sm text-red-400">{casualtiesCount}</span>
                  <button
                    type="button"
                    onClick={() => setCasualtiesCount(casualtiesCount + 1)}
                    className="w-8 h-8 rounded-lg bg-slate-800 text-white font-bold"
                  >+</button>
                </div>
              </div>
            </div>

            {/* Step 5: Contact Details */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="space-y-1">
                <label className="text-xs text-slate-400">{t.name}</label>
                <input
                  type="text"
                  value={witnessName}
                  onChange={(e) => setWitnessName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400">{t.phone}</label>
                <input
                  type="tel"
                  value={witnessPhone}
                  onChange={(e) => setWitnessPhone(e.target.value)}
                  placeholder="+91 98..."
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white font-black py-3.5 rounded-xl shadow-lg shadow-red-950/60 flex items-center justify-center gap-2 text-sm tracking-wide active:scale-[0.99] transition"
            >
              <Send className="w-4 h-4" />
              {isSubmitting ? t.submitting : t.submit}
            </button>
          </form>
        )}

        {/* ----------------- INCIDENT TRACKING TAB ----------------- */}
        {activeTab === 'track' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Search Bar */}
            <form onSubmit={handleSearchTracking} className="flex gap-2">
              <input
                type="text"
                placeholder="Enter Incident ID (e.g. INC-20261124-...)"
                value={trackIncidentId}
                onChange={(e) => setTrackIncidentId(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono"
              />
              <button
                type="submit"
                className="bg-cyan-600 hover:bg-cyan-500 text-black font-bold px-4 rounded-xl text-xs"
              >
                Search
              </button>
            </form>

            {/* Tracked Incident Display */}
            {trackedIncident ? (
              <div className="tactical-card p-4 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div>
                    <span className="text-[10px] text-slate-400 font-mono">INCIDENT ID</span>
                    <h3 className="font-bold text-base text-white font-mono">{trackedIncident.incident_id}</h3>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 font-mono">SEVERITY TIER</span>
                    <div className="font-bold text-red-400 text-sm">{trackedIncident.severity}</div>
                  </div>
                </div>

                {/* Progress Stepper */}
                <div className="space-y-2 pt-1">
                  <div className="text-xs font-bold text-slate-300">Rescue Lifecycle Progress</div>
                  <div className="space-y-2">
                    {[
                      { key: 'Reported', label: t.statusReported },
                      { key: 'Verified', label: t.statusVerified },
                      { key: 'Response Dispatched', label: t.statusDispatched },
                      { key: 'Rescue in Progress', label: t.statusRescue },
                      { key: 'Resolved', label: t.statusResolved },
                    ].map((step, idx, arr) => {
                      const statuses = ['Reported', 'Under Verification', 'Verified', 'Response Dispatched', 'En Route', 'On Scene', 'Rescue in Progress', 'Resolved'];
                      const currentIdx = statuses.indexOf(trackedIncident.status);
                      const stepIdx = statuses.indexOf(step.key);
                      const isComplete = currentIdx >= stepIdx;
                      const isCurrent = trackedIncident.status === step.key;

                      return (
                        <div key={step.key} className="flex items-center gap-3">
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                            isComplete ? 'bg-emerald-500 text-black' : isCurrent ? 'bg-cyan-500 text-black animate-pulse' : 'bg-slate-800 text-slate-500'
                          }`}>
                            {isComplete ? '✓' : idx + 1}
                          </div>
                          <span className={`text-xs ${isComplete || isCurrent ? 'text-white font-medium' : 'text-slate-500'}`}>
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* AI Reasoning Box */}
                {trackedIncident.ai_analysis_reasoning && (
                  <div className="bg-slate-900/90 border border-cyan-500/20 p-3 rounded-xl text-xs space-y-1">
                    <div className="font-bold text-cyan-400 flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5" /> AI Triage Assessment
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {trackedIncident.ai_analysis_reasoning}
                    </p>
                  </div>
                )}

                {/* Location Map */}
                <EmergencyMap
                  center={[trackedIncident.latitude, trackedIncident.longitude]}
                  selectedLocation={[trackedIncident.latitude, trackedIncident.longitude]}
                  zoom={14}
                  height="180px"
                />
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500 space-y-2">
                <Clock className="w-10 h-10 mx-auto text-slate-600" />
                <p className="text-xs">No active report selected for tracking.</p>
                <p className="text-[11px]">Submit an accident report or enter an ID above.</p>
              </div>
            )}
          </div>
        )}

        {/* ----------------- EMERGENCY DIRECTORY TAB ----------------- */}
        {activeTab === 'contacts' && (
          <div className="space-y-3 animate-in fade-in duration-200">
            <h2 className="font-bold text-sm text-white border-b border-slate-800 pb-2">
              Delhi NCR Emergency Helplines
            </h2>
            {[
              { title: 'National Emergency Service (ERSS)', num: '112', desc: 'Police, Ambulance & Fire integrated dispatch' },
              { title: 'Central Ambulance CATS Control Room', num: '102', desc: 'Advanced Life Support trauma transit' },
              { title: 'Delhi Fire Services (DFS)', num: '101', desc: 'Hydraulic rescue tenders & chemical fire units' },
              { title: 'Delhi Traffic Police Highway Patrol', num: '1095', desc: 'Traffic clearance & road blockade clearance' },
              { title: 'AIIMS Apex Trauma Emergency Hotline', num: '+91-11-2659-3200', desc: 'Level-1 Emergency Trauma Resuscitation' },
              { title: 'Safdarjung Hospital Emergency Desk', num: '+91-11-2616-5060', desc: 'Burns, Neuro-trauma and Intensive Care' },
            ].map((c) => (
              <a
                key={c.num}
                href={`tel:${c.num}`}
                className="tactical-card p-3.5 flex items-center justify-between hover:border-cyan-500/40 transition block"
              >
                <div>
                  <h3 className="font-bold text-xs text-white">{c.title}</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">{c.desc}</p>
                </div>
                <div className="flex items-center gap-1.5 bg-red-950 text-red-300 border border-red-800 px-3 py-1.5 rounded-lg text-xs font-bold font-mono">
                  <PhoneCall className="w-3 h-3" />
                  {c.num}
                </div>
              </a>
            ))}
          </div>
        )}
      </main>

      {/* Bottom Mobile Tab Bar */}
      <nav className="fixed bottom-0 max-w-md w-full bg-slate-900/95 border-t border-slate-800 backdrop-blur z-30 flex items-center justify-around py-2">
        <button
          onClick={() => setActiveTab('home')}
          className={`flex flex-col items-center gap-1 text-[11px] ${activeTab === 'home' ? 'text-red-400 font-bold' : 'text-slate-400'}`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Home SOS</span>
        </button>

        <button
          onClick={() => setActiveTab('report')}
          className={`flex flex-col items-center gap-1 text-[11px] ${activeTab === 'report' ? 'text-red-400 font-bold' : 'text-slate-400'}`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Report</span>
        </button>

        <button
          onClick={() => setActiveTab('track')}
          className={`flex flex-col items-center gap-1 text-[11px] ${activeTab === 'track' ? 'text-cyan-400 font-bold' : 'text-slate-400'}`}
        >
          <Activity className="w-4 h-4" />
          <span>Track</span>
        </button>

        <button
          onClick={() => setActiveTab('contacts')}
          className={`flex flex-col items-center gap-1 text-[11px] ${activeTab === 'contacts' ? 'text-cyan-400 font-bold' : 'text-slate-400'}`}
        >
          <PhoneCall className="w-4 h-4" />
          <span>Helplines</span>
        </button>
      </nav>
    </div>
  );
};
