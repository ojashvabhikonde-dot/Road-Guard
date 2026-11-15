"""Risk evaluation module for ROADGUARD AI Service.

Provides data models and a deterministic risk calculation based on
observations derived from detections. The logic is intentionally simple
and fully deterministic so it can be unit‑tested without external
services.
"""

import uuid
from datetime import datetime
from typing import List

import yaml
from pydantic import BaseModel, Field

# Load configuration (reaction time, deceleration, safety margin, road multipliers)
# The config file lives at ``ai-service/config/risk_engine.yaml``.
# If the file cannot be read we fall back to sensible defaults.
CONFIG_PATH = "../config/risk_engine.yaml"
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
except Exception:
    _cfg = {}

REACTION_TIME = _cfg.get("reaction_time_seconds", 1.5)  # seconds
DECELERATION = _cfg.get("deceleration_m_per_s2", 5.0)   # m/s²
SAFETY_MARGIN = _cfg.get("safety_margin_meters", 2.0)  # meters
ROAD_MULTIPLIERS = _cfg.get("road_type_multipliers", {"highway": 0.8, "city": 1.0})


class Observation(BaseModel):
    """Observation derived from a detection.

    * ``detection_id`` – Unique ID of the detection (from DB).
    * ``speed_mps`` – Vehicle speed in meters per second.
    * ``distance_m`` – Distance to the intersection or conflict point in meters.
    * ``road_type`` – Optional road type label ("highway", "city", …).
    """

    detection_id: str = Field(..., description="Database detection primary key")
    speed_mps: float = Field(..., ge=0, description="Vehicle speed (m/s)")
    distance_m: float = Field(..., ge=0, description="Distance to conflict point (m)")
    road_type: str = Field("city", description="Road category for multiplier")


class RiskResult(BaseModel):
    """Result of a risk evaluation for a single observation."""

    detection_id: str
    risk_score: float = Field(..., ge=0, le=1, description="Normalized risk (0‑1)")
    risk_level: str = Field(..., description="Human‑readable risk level")
    description: str = Field(..., description="Explanation of the risk")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    def dict(self, *args, **kwargs):  # ensure JSON serialisable timestamps
        d = super().dict(*args, **kwargs)
        if isinstance(d.get("evaluated_at"), datetime):
            d["evaluated_at"] = d["evaluated_at"].isoformat()
        return d


def _risk_score(ob: Observation) -> float:
    """Calculate a raw risk score (higher = riskier).

    The formula is a simple Time‑to‑Collision (TTC) based metric:
    ``TTC = distance / speed`` (with guard for zero speed).
    ``stopping_distance = speed * REACTION_TIME + (speed**2) / (2 * DECELERATION)``.
    ``margin = stopping_distance - distance``.
    The risk is higher when ``margin`` is negative (i.e., cannot stop in time).
    The raw score is scaled to ``0‑1`` using a sigmoid‑like transformation.
    """
    if ob.speed_mps <= 0:
        return 0.0
    stopping_distance = (
        ob.speed_mps * REACTION_TIME + (ob.speed_mps ** 2) / (2 * DECELERATION)
    )
    margin = stopping_distance - ob.distance_m
    # Negative margin => high risk. Apply exponential decay.
    raw = max(-margin, 0) / (margin + SAFETY_MARGIN + 1e-6)
    # Apply road multiplier (more forgiving on highways)
    multiplier = ROAD_MULTIPLIERS.get(ob.road_type, 1.0)
    raw *= multiplier
    # Clamp and sigmoid‑ish normalize
    score = 1 - 1 / (1 + raw)
    return min(max(score, 0.0), 1.0)


def _risk_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def evaluate_batch(observations: List[Observation]) -> List[RiskResult]:
    """Evaluate a list of observations and return risk results.

    The function is pure – it does not perform any I/O. Persistence is the
    responsibility of the caller (the FastAPI endpoint in ``main.py``).
    """
    results: List[RiskResult] = []
    for obs in observations:
        score = _risk_score(obs)
        level = _risk_level(score)
        description = (
            f"Vehicle {obs.detection_id} with speed {obs.speed_mps:.1f} m/s "
            f"and distance {obs.distance_m:.1f} m yields a {level} risk (score {score:.2f})."
        )
        results.append(
            RiskResult(
                detection_id=obs.detection_id,
                risk_score=score,
                risk_level=level,
                description=description,
            )
        )
    return results

