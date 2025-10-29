import json
import os
from statistics import mean
from typing import Dict, Any, Optional


def clamp(x: float, low: float, high: float) -> float:
    """
    a function that keeps values in the range [low, high] ([0, 1])
    """
    return max(low, min(high, x))


def aggregate_prior(
    related_themes: list[dict[str, Any]],
    min_prior: float = 0.05,
    max_prior: float = 0.95,
) -> float:
    """
    a function that aggregates the prior knowledge from related themes
    by calculating the mean of the mastery coeffs
    """
    if not related_themes:
        return min_prior
    avg = mean(rt["mastery_coefficient"] for rt in related_themes)
    return clamp(avg, min_prior, max_prior)


class TrainedParamsStore:
    """
    Trained pyBKT model's params per theme.
    Expected structure of the JSON params file:
    {
      "theme_id": {"transition": 0.15, "guess": 0.2, "slip": 0.1, "prior": 0.1}
    }
    """

    def __init__(self, params: Dict[str, Dict[str, float]]):
        self._params = params

    @classmethod
    def from_json_path(cls, path: str) -> "TrainedParamsStore":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    @classmethod
    def from_env(cls) -> Optional["TrainedParamsStore"]:
        json_path = os.getenv("BKT_PARAMS_JSON")
        if not json_path or not os.path.exists(json_path):
            return None
        return cls.from_json_path(json_path)

    def get(self, theme_id: str) -> Optional[Dict[str, float]]:
        return self._params.get(theme_id)


def predict_success(payload: dict, store: TrainedParamsStore | None) -> dict:
    """
    a function that predicts the success probability of learning a new theme
    """
    theme_id = payload["theme_id"]
    params = (store.get(theme_id) if store else None) or {
        # fallback if there are no trained params from pyBKT model
        "transition": float(os.getenv("BKT_T", 0.15)),
        "guess": float(os.getenv("BKT_G", 0.20)),
        "slip": float(os.getenv("BKT_S", 0.10)),
        "prior": float(os.getenv("BKT_PRIOR", 0.10)),
    }

    L0 = aggregate_prior(payload.get("related_themes", []))
    if not payload.get("related_themes"):
        L0 = clamp(float(params.get("prior", 0.10)), 0.0, 1.0)

    T = float(params["transition"])
    G = float(params["guess"])
    S = float(params["slip"])

    L1 = L0 + (1.0 - L0) * T
    p_correct = L1 * (1.0 - S) + (1.0 - L1) * G
    return {
        "theme_id": theme_id,
        "success_prediction": round(clamp(p_correct, 0.0, 1.0), 4),
    }
