"""
roadsafety/backend/routers/ai.py
================================
AI Triage intelligence endpoints reusing the Zero-Shot NLP and heuristic engine.
"""

from fastapi import APIRouter
from ..schemas import AIAnalyzeRequest, AIAnalysisResponse
from ..database import BASE_DIR

import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.triage_engine import IntelligentTriageEngine

router = APIRouter(prefix="/api/ai", tags=["AI Intelligence Engine"])
_triage_engine = IntelligentTriageEngine()


@router.post("/analyze", response_model=AIAnalysisResponse)
def analyze_incident_text(payload: AIAnalyzeRequest):
    """
    On-demand AI accident analysis: extracts vehicle count, casualties, fire,
    hazard tier, severity, and generates an explainable reasoning summary.
    """
    triage = _triage_engine.analyze(
        witness_text=payload.text,
        visual_tags=payload.visual_tags,
    )

    veh_count = payload.vehicles_hint or 1
    cas_count = payload.casualties_hint or 0
    if "vehicle_count" in triage.entities and veh_count == 1:
        try:
            veh_count = int(triage.entities["vehicle_count"][0])
        except Exception:
            pass
    if "casualty_count" in triage.entities and cas_count == 0:
        try:
            cas_count = int(triage.entities["casualty_count"][0])
        except Exception:
            pass

    fire = "Fire/Explosion" in triage.top_label or "fire" in payload.text.lower() or "burning" in payload.text.lower()
    hazard_level = "High" if triage.urgency_index >= 7.0 else "Moderate"

    explanation = (
        f"AI classified this scene as '{triage.top_label}' with Urgency Index {triage.urgency_index:.2f}/10.00 ({triage.severity_level}). "
        f"Extracted {veh_count} vehicle(s), {cas_count} casualty/injuries. "
        f"Recommended units: {', '.join(triage.recommended_units)}."
    )

    return {
        "category": triage.top_label,
        "vehicle_count": veh_count,
        "reported_casualties": cas_count,
        "fire_mentioned": fire,
        "hazard_level": hazard_level,
        "severity": triage.severity_level,
        "urgency_index": triage.urgency_index,
        "golden_hour_sla_min": triage.golden_hour_sla_min,
        "recommended_resources": triage.recommended_units,
        "explanation": explanation,
        "confidence_score": 0.89,
    }
