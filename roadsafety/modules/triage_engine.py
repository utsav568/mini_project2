"""
IntelligentTriageEngine
=======================
On-device Zero-Shot Classification triage engine with multi-modal evidence
support, comprehensive emergency entity extraction, negation handling,
and mathematical Urgency Index scoring.

Responsibilities:
  - Load and cache the ZSC pipeline (DistilBERT/MNLI) if available.
  - Robust on-device keyword/semantic fallback classifier with negation awareness.
  - Compute math-bounded Urgency Index (1.00 – 10.00).
  - Extract numeric entities (vehicle counts, casualties, fire, hazmat, speeds).
  - Golden Hour SLA target computation based on emergency medicine guidelines.
  - Multi-modal evidence fusion (supporting camera/CCTV/witness image damage tags).
"""

from __future__ import annotations

import re
import math
import logging
from functools import lru_cache
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANDIDATE_LABELS: list[str] = [
    "Fire/Explosion",
    "Critical Medical Trauma",
    "Minor Collision",
    "Hazardous Material Leak",
    "Vehicle Entrapment",
]

# Severity multipliers per label (used to bias the Urgency Index)
SEVERITY_WEIGHTS: dict[str, float] = {
    "Fire/Explosion":          1.00,
    "Critical Medical Trauma": 0.95,
    "Vehicle Entrapment":      0.85,
    "Hazardous Material Leak": 0.80,
    "Minor Collision":         0.30,
}

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class TriageResult(NamedTuple):
    top_label: str
    urgency_index: float          # 1.00 – 10.00
    label_scores: dict[str, float]
    entities: dict[str, list[str]]
    recommended_units: list[str]
    golden_hour_sla_min: float = 10.0
    severity_level: str = "HIGH"


# ---------------------------------------------------------------------------
# Pipeline loader (module-level singleton via lru_cache)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_pipeline():
    """Load the zero-shot classification pipeline if torch/transformers are installed."""
    model_candidates = [
        "typeform/distilbert-base-uncased-mnli",
        "cross-encoder/nli-MiniLM2-L6-H768",
        "facebook/bart-large-mnli",
    ]
    try:
        from transformers import pipeline  # type: ignore
        for model_name in model_candidates:
            try:
                logger.info("Loading ZSC pipeline — %s …", model_name)
                kwargs: dict = {
                    "model": model_name,
                    "device": -1,  # CPU
                }
                try:
                    pipe = pipeline("zero-shot-classification", **kwargs)
                except TypeError:
                    pipe = pipeline(
                        "zero-shot-classification",
                        model=model_name,
                        device=-1,
                        framework="pt",
                    )
                logger.info("ZSC pipeline loaded: %s", model_name)
                return pipe
            except Exception as model_exc:
                logger.warning("Model %s failed: %s. Trying next …", model_name, model_exc)
                continue
        logger.info("Transformers pipeline candidates not loaded. Using intelligent heuristic fallback.")
        return None
    except Exception as exc:
        logger.info("Transformers not installed (%s). Using high-accuracy intelligent heuristic engine.", exc)
        return None


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------

_ENTITY_PATTERNS: dict[str, str] = {
    "vehicle_count": r"""
        (?:
            (?P<digit>\d+)
            |
            (?P<word>one|two|three|four|five|six|seven|eight|nine|ten)
        )
        \s*
        (?:car|truck|vehicle|bus|van|lorry|suv|motorcycle|bike|auto|tempo)s?
    """,
    "casualty_count": r"""
        (?:
            (?P<digit>\d+)
            |
            (?P<word>one|two|three|four|five|six|seven|eight|nine|ten)
        )
        \s*
        (?:casualt(?:y|ies)|injur(?:ed|ies)|victim|person|people|passenger|survivor)s?
    """,
    "fire_mention":    r"\b(?:fire|flame|flames|burning|ablaze|explosion|blast|smoke|inferno)\b",
    "hazmat_mention":  r"\b(?:chemical|gas|leak|spill|fuel|toxic|fumes|hazmat|acid)\b",
    "speed_mention":   r"(?P<speed>\d+)\s*(?:km/h|mph|kph)",
    "entrapment_mention": r"\b(?:trapped|pinned|stuck|entrap|entrapped|crushed|under\s+the\s+truck)\b",
}

_WORD_TO_NUM: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_NEGATION_PATTERNS = [
    r"\b(?:no|zero|without|neither)\s+(?:injur|casualt|fatal|death|victim|blood)",
    r"\b(?:no\s+one|nobody)\s+(?:is\s+)?(?:injur|hurt|killed|dead)",
    r"\bno\s+injuries\s+reported\b",
]


def _check_negation(text_lower: str) -> bool:
    """Detect phrases asserting lack of injuries or casualties."""
    for pattern in _NEGATION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _extract_entities(text: str) -> dict[str, list[str]]:
    """Return a dict of entity type -> list of extracted string values."""
    entities: dict[str, list[str]] = {}
    text_lower = text.lower()

    # Check for no casualties negation first
    has_no_injuries = _check_negation(text_lower)

    for entity_type, pattern in _ENTITY_PATTERNS.items():
        if entity_type == "casualty_count" and has_no_injuries:
            entities["casualty_count"] = ["0"]
            continue

        matches = re.findall(pattern, text_lower, re.VERBOSE | re.IGNORECASE)
        if matches:
            flat: list[str] = []
            for m in matches:
                if isinstance(m, tuple):
                    val = next((g for g in m if g), None)
                    if val:
                        flat.append(str(_WORD_TO_NUM.get(val, val)))
                else:
                    flat.append(str(m))
            if flat:
                entities[entity_type] = flat

    if has_no_injuries and "casualty_count" not in entities:
        entities["casualty_count"] = ["0"]

    return entities


# ---------------------------------------------------------------------------
# Urgency Index computation
# ---------------------------------------------------------------------------

def _compute_urgency(
    label_scores: dict[str, float],
    entities: dict[str, list[str]],
    visual_bonus: float = 0.0,
) -> float:
    """
    Compute an Urgency Index in [1.00, 10.00].

    Formula:
        base = sum(score_i * severity_weight_i) for all labels i
        bonus = entity clusters (casualties, fire, hazmat, entrapment) + visual evidence
        raw   = sigmoid(base * 6 - 3) * 9 + 1
        final = clamp(raw + bonus, 1.0, 10.0)
    """
    base = sum(
        score * SEVERITY_WEIGHTS.get(label, 0.5)
        for label, score in label_scores.items()
    )

    # Sigmoid stretch so mid-confidence -> mid urgency
    sigmoid_val = 1.0 / (1.0 + math.exp(-(base * 6.0 - 3.0)))
    raw_urgency = sigmoid_val * 9.0 + 1.0

    # Entity-based bonuses
    bonus = visual_bonus
    if "casualty_count" in entities:
        try:
            n = int(entities["casualty_count"][0])
            if n == 0:
                bonus -= 0.8  # explicit zero casualties reduces urgency
            else:
                bonus += min(n * 0.35, 1.8)
        except ValueError:
            bonus += 0.3
    if "fire_mention" in entities:
        bonus += 0.5
    if "hazmat_mention" in entities:
        bonus += 0.4
    if "entrapment_mention" in entities:
        bonus += 0.6

    return round(min(max(raw_urgency + bonus, 1.0), 10.0), 2)


# ---------------------------------------------------------------------------
# Unit recommendation & Golden Hour SLA
# ---------------------------------------------------------------------------

def _recommend_units(top_label: str, urgency: float, entities: dict) -> list[str]:
    units: list[str] = []
    if top_label == "Fire/Explosion":
        units = ["🚒 Advanced Fire Engine", "🚑 Rapid ALS Paramedic", "👮 Police Traffic Escort"]
    elif top_label == "Critical Medical Trauma":
        units = ["🚑 Advanced Life Support (ALS)", "🏥 CATS Trauma Ambulance", "👮 Emergency Highway Patrol"]
    elif top_label == "Vehicle Entrapment":
        units = ["🚒 Heavy Hydraulic Rescue (Jaws of Life)", "🚑 Trauma Paramedic Unit", "👮 Traffic Control Unit"]
    elif top_label == "Hazardous Material Leak":
        units = ["☣️ National HazMat Containment Team", "🚒 Industrial Foam Tender", "👮 Highway Exclusion Unit"]
    else:  # Minor Collision
        units = ["🚑 Basic Life Support Ambulance", "👮 Local PCR Police Van"]

    if urgency >= 8.5:
        if "🏥 AIIMS Air Trauma Helicopter" not in units:
            units.append("🏥 AIIMS Air Trauma Helicopter")
    return units


def _compute_golden_hour_sla(urgency: float) -> tuple[float, str]:
    """
    Standard emergency medicine response SLA:
      Urgency >= 8.0: CRITICAL (Golden Hour SLA: 8.0 min max)
      Urgency >= 6.0: HIGH     (Golden Hour SLA: 12.0 min max)
      Urgency >= 4.0: MODERATE (Golden Hour SLA: 20.0 min max)
      Urgency < 4.0:  LOW      (Golden Hour SLA: 30.0 min max)
    """
    if urgency >= 8.0:
        return 8.0, "CRITICAL"
    elif urgency >= 6.0:
        return 12.0, "HIGH"
    elif urgency >= 4.0:
        return 20.0, "MODERATE"
    else:
        return 30.0, "LOW"


# ---------------------------------------------------------------------------
# Main engine class
# ---------------------------------------------------------------------------

class IntelligentTriageEngine:
    """
    Zero-Shot classification triage engine with entity extraction,
    negation understanding, multi-modal evidence fusion, and urgency scoring.
    """

    def __init__(self) -> None:
        self._pipe = None  # Lazy loaded

    def analyze(
        self,
        witness_text: str,
        visual_tags: Optional[list[str]] = None,
        visual_severity_bonus: float = 0.0,
    ) -> TriageResult:
        """
        Full triage pipeline on witness_text and optional visual evidence tags.

        Returns a TriageResult with scores, urgency index, entities, and Golden Hour SLA.
        """
        if not witness_text or not witness_text.strip():
            raise ValueError("Witness text must not be empty.")

        self._ensure_pipeline()

        # Classification
        label_scores = self._classify(witness_text)

        # Entity extraction
        entities = _extract_entities(witness_text)

        # If visual tags are provided (e.g., from CCTV or photo upload), enrich entities & bonus
        if visual_tags:
            entities["visual_evidence"] = visual_tags
            for tag in visual_tags:
                tag_l = tag.lower()
                if "fire" in tag_l or "smoke" in tag_l:
                    visual_severity_bonus += 0.4
                    label_scores["Fire/Explosion"] = label_scores.get("Fire/Explosion", 0) + 0.2
                if "rollover" in tag_l or "entrap" in tag_l or "crush" in tag_l:
                    visual_severity_bonus += 0.5
                    label_scores["Vehicle Entrapment"] = label_scores.get("Vehicle Entrapment", 0) + 0.25
                if "deformation" in tag_l or "airbag" in tag_l:
                    visual_severity_bonus += 0.3
                    label_scores["Critical Medical Trauma"] = label_scores.get("Critical Medical Trauma", 0) + 0.2

            # Normalize scores after visual update
            tot = sum(label_scores.values()) or 1.0
            label_scores = {k: round(v / tot, 4) for k, v in label_scores.items()}

        # Top label by score
        top_label = max(label_scores, key=lambda k: label_scores[k])

        # Urgency index
        urgency = _compute_urgency(label_scores, entities, visual_bonus=visual_severity_bonus)

        # SLA & severity
        sla_min, severity_level = _compute_golden_hour_sla(urgency)

        # Unit recommendation
        units = _recommend_units(top_label, urgency, entities)

        return TriageResult(
            top_label=top_label,
            urgency_index=urgency,
            label_scores=label_scores,
            entities=entities,
            recommended_units=units,
            golden_hour_sla_min=sla_min,
            severity_level=severity_level,
        )

    def _ensure_pipeline(self) -> None:
        if self._pipe is None:
            self._pipe = _load_pipeline()

    def _classify(self, text: str) -> dict[str, float]:
        """Run ZSC pipeline or fall back to high-accuracy heuristic engine."""
        if self._pipe is not None:
            try:
                result = self._pipe(text, CANDIDATE_LABELS, multi_label=False)
                return dict(zip(result["labels"], result["scores"]))
            except Exception as exc:
                logger.warning("Pipeline inference failed (%s). Using heuristic.", exc)

        return self._heuristic_classify(text)

    @staticmethod
    def _heuristic_classify(text: str) -> dict[str, float]:
        """
        High-accuracy keyword and semantic pattern fallback classifier
        with context awareness and negation handling.
        """
        text_l = text.lower()
        has_no_injuries = _check_negation(text_l)

        keyword_map: dict[str, list[str]] = {
            "Fire/Explosion": [
                "fire", "explosion", "flame", "flames", "burning", "ablaze", "blast",
                "smoke", "ignited", "ignite", "fuel burning", "combustion", "inferno",
            ],
            "Critical Medical Trauma": [
                "blood", "bleeding", "unconscious", "not breathing", "cardiac", "trauma",
                "critical", "severe injury", "severe injuries", "injured", "injuries",
                "casualty", "casualties", "victim", "victims", "fatal", "fatality",
                "dead", "hurt", "coma", "fracture", "head-on", "collision", "crash",
                "spine", "stroke", "ambulance", "paramedic", "life support",
            ],
            "Vehicle Entrapment": [
                "trapped", "pinned", "stuck", "entrap", "entrapped", "door jammed",
                "crushed", "cut out", "roof crushed", "rolled over", "rollover",
                "overturned", "under the truck", "under vehicle", "inversion", "jaws of life",
            ],
            "Hazardous Material Leak": [
                "chemical", "gas leak", "fuel leak", "tanker leak", "spill", "spilling",
                "hazmat", "toxic", "fumes", "acid", "flammable", "diesel spill",
                "petrol leak", "hazard", "corrosive", "vapour",
            ],
            "Minor Collision": [
                "fender bender", "minor", "scratch", "scratched", "small bump", "dent",
                "dented", "tap", "rear-ended", "side-swiped", "minor damage", "low speed",
                "bumper damage", "glass shattered",
            ],
        }

        raw: dict[str, float] = {}
        for label, keywords in keyword_map.items():
            hits = 0.0
            for kw in keywords:
                if kw in text_l:
                    # Multi-word matches carry higher confidence
                    weight = 2.0 if " " in kw else 1.0
                    hits += weight
            raw[label] = hits

        # If witness stated no casualties/injuries, suppress Critical Medical Trauma and boost Minor Collision
        if has_no_injuries:
            raw["Critical Medical Trauma"] = 0.0
            raw["Minor Collision"] = raw.get("Minor Collision", 0.0) + 3.0

        # If zero keywords matched across the entire vocabulary
        if sum(raw.values()) == 0.0:
            # Check for generic traffic terms
            if any(w in text_l for w in ["car", "road", "vehicle", "traffic", "highway", "expressway"]):
                raw["Minor Collision"] = 1.0
            else:
                raw["Minor Collision"] = 1.0

        total = sum(raw.values())
        prior = 0.05
        scores = {label: (raw[label] + prior) / (total + prior * len(raw)) for label in raw}

        # Re-normalize to sum to 1.0
        s_total = sum(scores.values())
        return {label: round(v / s_total, 4) for label, v in scores.items()}
