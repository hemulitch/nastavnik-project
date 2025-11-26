from dataclasses import dataclass
from typing import Any, Optional
import os

def clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    """
    Перевод значений в диапазон [low, high]
    """
    return max(low, min(high, x))

@dataclass
class BKTParams:
    transition: float = 0.15   # T
    guess: float = 0.20        # G
    slip: float = 0.10         # S
    prior: float = 0.10        # L0 default


def predict_action_success(request: dict[str, Any]) -> dict[str, Any]:
    """
    Оценка вероятности успешного выполнения учебного действия
    """
    params = BKTParams(
        transition=float(os.getenv("BKT_T", 0.15)),
        guess=float(os.getenv("BKT_G", 0.20)),
        slip=float(os.getenv("BKT_S", 0.10)),
        prior=float(os.getenv("BKT_PRIOR", 0.10)),
    )

    theme = request.get("theme", {})
    theme_id = theme.get("theme_id", "unknown_theme")
    lesson_index = request.get("lesson_index", 1)
    action_index = request.get("action_index", 1)

    # Берём lesson_mastery как prior
    lesson_mastery_raw = request.get("lesson_mastery")
    if lesson_mastery_raw is not None:
        L_prior = clamp(float(lesson_mastery_raw))
    else:
        # если вдруг мастерства для урока нет, берем мастерство для темы
        theme_mastery_raw = theme.get("mastery_coefficient")
        if theme_mastery_raw is not None:
            L_prior = clamp(float(theme_mastery_raw))
        else:
            L_prior = params.prior
    
    Lk = 1.0 - (1.0 - L_prior) * (1.0 - params.transition)

    # итоговая вероятность успеха
    success_prob = Lk * (1.0 - params.slip) + (1.0 - Lk) * params.guess
    success_prob = clamp(success_prob)

    return {
        "theme_id": theme_id,
        "lesson_index": lesson_index,
        "action_index": action_index,
        "success_prediction": round(success_prob, 3),
    }

if __name__ == "__main__":
    example_request = {
        "theme": {
            "theme_id": "math_004",
            "mastery_coefficient": 0.76,
            "time_spent": 100,
        },
        "related_themes": [
            {
                "theme_id": "math_003",
                "mastery_coefficient": 0.85,
                "time_spent": 4000,
            },
            {
                "theme_id": "math_002",
                "mastery_coefficient": 0.72,
                "time_spent": 3600,
            },
        ],
        "lesson_index": 3,
        "lesson_mastery": 0.75,
        "total_lessons": 10,
        "action_index": 5,
        "action_type": "test",
        "action_difficulty": 0.7,
    }

    result = predict_action_success(example_request)
    print(result)