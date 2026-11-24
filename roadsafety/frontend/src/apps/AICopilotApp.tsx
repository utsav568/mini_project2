import React, { useState } from 'react';
import {
  Brain,
  Sparkles,
  AlertTriangle,
  Flame,
  Truck,
  Activity,
  Clock,
  ShieldCheck,
  Send,
  Zap,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { apiAIAnalyze, apiReportIncident } from '../api';

interface AIResult {
  category: string;
  vehicle_count: number;
  reported_casualties: number;
  fire_mentioned: boolean;
  hazard_level: string;
  severity: string;
  urgency_index: number;
  golden_hour_sla_min: number;
  recommended_resources: string[];
  explanation: string;
  confidence_score: number;
}

const PRESETS = [
  {
    title: '💥 Fuel Depot Explosion',
    text: 'Major explosion at the central fuel depot on Outer Ring Road! Three vehicles engulfed in flames, thick toxic black smoke spreading, two casualties trapped near blast zone.',
    tags: ['Fire / Smoke', 'Structural Rupture']
  },
  {
    title: '🚗 NH-48 Fog Pileup',
    text: 'Massive 5-car highway pileup in dense morning fog on NH-48 near Gurgaon border. Four people severely injured and bleeding, two vehicles rolled over with trapped passengers.',
    tags: ['Structural Rupture', 'Airbag Deployed']
  },
  {
    title: '☣️ Chemical Tanker Leak',
    text: 'Industrial chemical tanker truck ruptured on DND Flyway. Corrosive solvent leaking across both lanes, severe toxic fumes, drivers coughing and evacuating.',
    tags: ['Chemical Spillage', 'Fire / Smoke']
  },
  {
    title: '🚙 Minor Fender Bender',
    text: 'Low-speed rear end collision between two sedans at Connaught Place Inner Circle. Slight bumper damage, zero casualties, both drivers arguing.',
    tags: []
  }
];

export const AICopilotApp: React.FC = () => {
  const [statement, setStatement] = useState(PRESETS[0].text);
  const [selectedTags, setSelectedTags] = useState<string[]>(PRESETS[0].tags);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiResult, setAiResult] = useState<AIResult | null>(null);
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);

  const availableTags = [
    'Fire / Smoke',
    'Structural Rupture',
    'Chemical Spillage',
    'Airbag Deployed',
    'Vehicle Rollover'
  ];

  const handleToggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleRunAI = async () => {
    if (!statement.trim()) return;
    setIsAnalyzing(true);
    setDispatchSuccess(null);
    try {
      const res = await apiAIAnalyze(statement, selectedTags);
      setAiResult(res);
    } catch (err: any) {
      alert(err.message || 'AI Triage service unreachable');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleInstantDispatch = async () => {
    if (!aiResult) return;
    setIsDispatching(true);
    try {
      const incident = await apiReportIncident({
        witness_statement: statement,
        latitude: 28.5672,
        longitude: 77.2100,
        witness_name: 'AI CAD Copilot Auto-Dispatch',
        witness_phone: '+91-11-2659-3200',
        category: aiResult.category,
        reported_casualties: aiResult.reported_casualties,
        vehicles_count: aiResult.vehicle_count,
        hazards: [aiResult.hazard_level],
        visual_tags: selectedTags
      });
      setDispatchSuccess(incident.incident_id);
    } catch (err: any) {
      alert(err.message || 'Failed to dispatch from AI triage');
    } finally {
      setIsDispatching(false);
    }
  };

  const getUrgencyColor = (score: number) => {
    if (score >= 8.5) return 'from-red-600 to-rose-700 text-red-400 border-red-500';
    if (score >= 6.5) return 'from-orange-600 to-amber-700 text-orange-400 border-orange-500';
    if (score >= 4.0) return 'from-yellow-600 to-amber-600 text-yellow-400 border-yellow-500';
    return 'from-emerald-600 to-teal-700 text-emerald-400 border-emerald-500';
  };

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6 text-slate-100 pb-20">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl relative overflow-hidden">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-purple-900/50">
              <Brain className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black text-white tracking-tight">AI Emergency Triage Copilot</h1>
                <span className="text-[10px] bg-purple-950 text-purple-400 border border-purple-800 px-2 py-0.5 rounded font-mono font-bold">
                  ZERO-SHOT NLP v2.5
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time incident entity extraction, priority index classification & explainable dispatch reasoning
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-800/80 text-[11px] text-emerald-400 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              On-Device Model Active
            </span>
          </div>
        </div>
      </div>

      {/* Preset Scenarios Selector */}
      <div className="space-y-2">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          Load Benchmark Emergency Scenarios
        </span>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => {
                setStatement(p.text);
                setSelectedTags(p.tags);
                setAiResult(null);
                setDispatchSuccess(null);
              }}
              className="bg-slate-900/90 border border-slate-800 hover:border-purple-500/50 p-2.5 rounded-xl text-left transition group active:scale-98"
            >
              <div className="font-bold text-xs text-slate-200 group-hover:text-purple-300 transition truncate">
                {p.title}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 line-clamp-1">
                {p.text}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Input Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
        <label className="text-xs font-bold text-slate-300 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-purple-400" />
            Witness Statement, 911 Call Transcript, or Telematics Log:
          </span>
          <span className="text-[11px] font-mono text-slate-500">{statement.length} chars</span>
        </label>
        <textarea
          rows={3}
          value={statement}
          onChange={(e) => setStatement(e.target.value)}
          placeholder="Enter accident description, visible vehicles, trapped casualties, fire, smoke, hazardous chemicals..."
          className="w-full bg-slate-950 border border-slate-800 focus:border-purple-500 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none transition resize-none font-mono"
        />

        {/* Multi-modal Evidence Tag Chips */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Multi-Modal Evidence Flags:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {availableTags.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => handleToggleTag(tag)}
                className={`text-xs px-2.5 py-1 rounded-lg border transition font-medium ${
                  selectedTags.includes(tag)
                    ? 'bg-purple-950 text-purple-300 border-purple-700'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-300'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Action Trigger */}
        <div className="flex justify-end pt-2">
          <button
            onClick={handleRunAI}
            disabled={isAnalyzing || !statement.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs tracking-wide shadow-lg shadow-purple-900/30 transition active:scale-95 disabled:opacity-50"
          >
            <Sparkles className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
            <span>{isAnalyzing ? 'Analyzing with Zero-Shot NLP...' : 'Run Real-Time AI Triage'}</span>
          </button>
        </div>
      </div>

      {/* AI Triage Results Display */}
      {aiResult && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {/* Urgency Score Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Activity className="w-3.5 h-3.5 text-red-400" /> Urgency Index
              </span>
              <div className="my-2">
                <div className="text-3xl font-black font-mono text-white flex items-baseline gap-1">
                  {aiResult.urgency_index.toFixed(2)}
                  <span className="text-xs text-slate-400 font-normal">/ 10.00</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                  <div
                    className={`h-full bg-gradient-to-r ${getUrgencyColor(aiResult.urgency_index)}`}
                    style={{ width: `${Math.min(100, aiResult.urgency_index * 10)}%` }}
                  />
                </div>
              </div>
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded border inline-block text-center ${
                aiResult.urgency_index >= 8.0 ? 'bg-red-950 text-red-400 border-red-800' : 'bg-amber-950 text-amber-400 border-amber-800'
              }`}>
                {aiResult.severity.toUpperCase()} PRIORITY
              </span>
            </div>

            {/* Golden Hour SLA */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-400" /> Golden Hour SLA
              </span>
              <div className="my-2">
                <div className="text-3xl font-black font-mono text-amber-400">
                  ≤ {aiResult.golden_hour_sla_min} <span className="text-sm font-normal text-slate-400">min</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Maximum trauma intervention window</p>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Critical Survival Window</span>
            </div>

            {/* Extracted Entities */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between md:col-span-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Truck className="w-3.5 h-3.5 text-cyan-400" /> Extracted Scene Entities
              </span>
              <div className="grid grid-cols-4 gap-2 my-2 text-center">
                <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Vehicles</span>
                  <span className="text-base font-bold text-cyan-400 font-mono">{aiResult.vehicle_count}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Casualties</span>
                  <span className="text-base font-bold text-red-400 font-mono">{aiResult.reported_casualties}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Fire/Smoke</span>
                  <span className={`text-base font-bold ${aiResult.fire_mentioned ? 'text-orange-400' : 'text-slate-500'}`}>
                    {aiResult.fire_mentioned ? 'YES' : 'NO'}
                  </span>
                </div>
                <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Hazmat</span>
                  <span className="text-base font-bold text-purple-400 font-mono">{aiResult.hazard_level}</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Predicted Category: <strong className="text-white">{aiResult.category}</strong></span>
                <span className="text-purple-400 font-mono">Confidence: {(aiResult.confidence_score * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          {/* Explainable Reasoning Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-purple-400" />
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Explainable AI Triage Rationale
              </h3>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-mono">
              {aiResult.explanation}
            </div>

            {/* Recommended Fleet Resources */}
            <div className="space-y-1.5 pt-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Automated Fleet Deployment Recommendations:
              </span>
              <div className="flex flex-wrap gap-2">
                {aiResult.recommended_resources.map((unit, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-cyan-800/60 text-cyan-300 font-medium text-xs shadow-sm"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                    {unit}
                  </span>
                ))}
              </div>
            </div>

            {/* Dispatch Action Button */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
              <div>
                {dispatchSuccess ? (
                  <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5 font-mono">
                    <CheckCircle2 className="w-4 h-4" /> Incident {dispatchSuccess} Logged & Fleet Dispatched!
                  </span>
                ) : (
                  <span className="text-xs text-slate-400">
                    Ready to execute automated dispatch protocol based on AI recommendation.
                  </span>
                )}
              </div>
              <button
                onClick={handleInstantDispatch}
                disabled={isDispatching || !!dispatchSuccess}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs tracking-wide shadow-lg shadow-red-900/30 transition active:scale-95 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isDispatching ? 'Dispatching Fleet...' : 'Dispatch Recommended Fleet'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
