import os
from statistics import mean
from typing import Any
from .models import PredictRequest
from dataclasses import dataclass

def clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    """keeps values in the range [low, high]"""
    return max(low, min(high, x))

@dataclass
class BKTParams:
    transition: float = 0.15   # T
    guess: float = 0.20        # G
    slip: float = 0.10         # S
    prior: float = 0.10        # L0 default
    steps: int = 1             # N

def aggregate_prior(
    related_themes: list[dict[str, Any]],
    min_prior: float = 0.05,
    max_prior: float = 0.95,
) -> float:
    """
    aggregates the prior knowledge from related themes
    by calculating the mean of the mastery coeffs
    """
    if not related_themes:
        return min_prior
    vals = [clamp(float(rt["mastery_coefficient"])) for rt in related_themes]
    if not vals:
        return min_prior
    avg = mean(vals)
    return clamp(avg, min_prior, max_prior)


def predict_success(request: PredictRequest) -> dict:
    theme_id = request["theme_id"]
    related_themes = request.get("related_themes", [])
    params = BKTParams(
        transition=float(os.getenv("BKT_T", 0.15)),
        guess=float(os.getenv("BKT_G", 0.20)),
        slip=float(os.getenv("BKT_S", 0.10)),
        prior=float(os.getenv("BKT_PRIOR", 0.10)),
        steps=int(os.getenv("BKT_STEPS", 1))
    )

    if related_themes:
        L0 = aggregate_prior(related_themes)
    else:
        L0 = params.prior

    Lk = 1.0 - (1.0 - L0) * ((1.0 - params.transition) ** params.steps)
    prob = Lk * (1.0 - params.slip) + (1.0 - Lk) * params.guess
    return {
        "theme_id": theme_id,
        "success_prediction": round(clamp(prob), 2)
    }
