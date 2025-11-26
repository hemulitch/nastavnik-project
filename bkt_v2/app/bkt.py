import os
from dataclasses import dataclass
from .models import PredictRequest

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


def predict_action_success(request: PredictRequest) -> dict:
    """
    Оценка вероятности успешного выполнения учебного действия
    """
    params = BKTParams(
        transition=float(os.getenv("BKT_T", 0.15)),
        guess=float(os.getenv("BKT_G", 0.20)),
        slip=float(os.getenv("BKT_S", 0.10)),
        prior=float(os.getenv("BKT_PRIOR", 0.10)),
    )

    theme_id = request.theme.theme_id,
    lesson_index = request.lesson_index
    action_index = request.action_index

    # Берём lesson_mastery как prior
    lesson_mastery_raw = request.lesson_mastery
    if lesson_mastery_raw is not None:
        L_prior = clamp(float(lesson_mastery_raw))
    else:
        # если вдруг мастерства для урока нет, берем мастерство для темы
        theme_mastery_raw = theme.mastery_coefficient
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
