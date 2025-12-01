import os
from dataclasses import dataclass
from .models import PredictRequest
from typing import Tuple

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


def estimate_theme_level(request: PredictRequest, params: BKTParams) -> float:
    """
    Оценка уровня знания по теме 

    Используем:
    - mastery_coefficient по теме, если есть, иначе из параметров 
    - среднее mastery по связанным темам
    - время изучения темы 
    - прогресс по теме (lesson_index / total_lessons)
    """
    theme = request.theme
    related = request.related_themes

    mastery = theme.mastery_coefficient

    if mastery is not None:
        base = mastery
    else:
        base = params.prior

    # связанные темы
    if related:
        rel_masteries = [t.mastery_coefficient for t in related if t.mastery_coefficient is not None]
        if rel_masteries:
            rel_avg = sum(rel_masteries) / len(rel_masteries)
            W_RELATED = 0.2  # вклад связанных тем
            base = (1.0 - W_RELATED) * base + W_RELATED * rel_avg

    # время изучения темы
    time_spent = theme.time_spent
    if time_spent is not None:
        # предполагаем, что максимум эффекта на 10 часах изучения
        norm = min(time_spent, 36000) / 36000.0
        TIME_ALPHA = 0.2  # максимум примерно +-0.1 к base
        base = base + TIME_ALPHA * (norm - 0.5)

    # прогресс по теме
    total_lessons = request.total_lessons
    if total_lessons:
        progress = clamp(request.lesson_index / total_lessons)
        W_PROGRESS = 0.2
        base = (1.0 - W_PROGRESS) * base + W_PROGRESS * progress

    return clamp(base)


def compute_prior(request: PredictRequest, params: BKTParams) -> float:
    """
    Оценка текущей вероятности знания навыка

    Идея:
    - theme_level: глобальная оценка по теме
    - lesson_mastery: локальная оценка по текущему уроку
    - чем больше действий уже сделано в уроке (action_index), тем сильнее вклад lesson_mastery.
    """
    theme_level = estimate_theme_level(request, params)

    lesson_mastery = request.lesson_mastery
    if lesson_mastery is None:
        # если нет локальной оценки - полагаемся на глобальную
        return theme_level

    lesson_level = clamp(lesson_mastery)

    # вес lesson_mastery растёт с action_index
    action_index = request.action_index
    K = 10.0  # после 10 действий урок считаем достаточно хорошо измеренным
    w_lesson = clamp((action_index - 1) / K)  # от 0 до 1
    w_theme = 1.0 - w_lesson

    L_t = w_theme * theme_level + w_lesson * lesson_level
    return clamp(L_t)


def effective_params_for_action(action, base: BKTParams) -> BKTParams:
    """
    Адаптация guess/slip под конкретное действие.

    Идея: Чем сложнее действие, тем:
    - ниже шанс угадать не зная (guess уменьшается)
    - выше риск ошибиться даже зная (slip увеличивается).
    """
    difficulty = action.action_difficulty or 0.5
    diff_centered = difficulty - 0.5
    SCALE = 0.6  # сила влияния сложности

    guess = clamp(base.guess * (1.0 - SCALE * diff_centered))
    slip  = clamp(base.slip  * (1.0 + SCALE * diff_centered))

    return BKTParams(
        transition=base.transition,
        guess=guess,
        slip=slip,
        prior=base.prior,
    )


def predict_action(request: PredictRequest, range: Tuple[float, float] = (0.4, 0.6)) -> dict:
    """
    Считает вероятность успеха для каждого действия и выбирает одно действие.
    """
    params = BKTParams(
        guess=float(os.getenv("BKT_G", 0.20)),
        slip=float(os.getenv("BKT_S", 0.10)),
        prior=float(os.getenv("BKT_PRIOR", 0.10)),
    )

    L_t = compute_prior(request, params)
    
    actions = request.actions
    predictions = []
    for action in actions:
        eff = effective_params_for_action(action, params)

        p_success = L_t * (1.0 - eff.slip) + (1.0 - L_t) * eff.guess
        p_success = clamp(p_success)

        pred = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "action_difficulty": action.action_difficulty,
            "success_prediction": round(p_success, 3),
        }
        predictions.append(pred)

    low, high = range
    center = (low + high) / 2.0

    in_range = [p for p in predictions if low <= p["success_prediction"] <= high]

    if in_range:
        # выбираем действие, ближе всего к центру диапазона 
        chosen = min(in_range, key=lambda p: abs(p["success_prediction"] - center))
    else:
        # берём то, что ближе всего к центру, даже если вне диапазона
        chosen = min(predictions, key=lambda p: abs(p["success_prediction"] - center))

    return {
        "theme_id": request.theme.theme_id,
        "lesson_index": request.lesson_index,
        "action_index": request.action_index,
        "actions": predictions,
        "chosen_action": chosen,
    }