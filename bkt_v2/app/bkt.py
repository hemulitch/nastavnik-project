import os
from dataclasses import dataclass
from typing import Tuple, List
from app.models import PredictRequest


def clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    """
    Перевод значений в диапазон [low, high]
    """
    return max(low, min(high, float(x)))


@dataclass(frozen=True)
class BKTParams:
    transition: float = 0.05  # T
    guess: float = 0.20       # G
    slip: float = 0.10        # S
    prior: float = 0.10       # L0


def get_params_from_env() -> BKTParams:
    return BKTParams(
        transition=float(os.getenv("BKT_T", "0.05")),
        guess=float(os.getenv("BKT_G", "0.20")),
        slip=float(os.getenv("BKT_S", "0.10")),
        prior=float(os.getenv("BKT_PRIOR", "0.10")),
    )


def bkt_update(L: float, guess: float, slip: float, transition: float, correct: bool) -> float:
    """
    Обновление значения L на основе результата действия
    """
    L = clamp(L)
    guess = clamp(guess)
    slip = clamp(slip)
    transition = clamp(transition)

    if correct:
        num = L * (1.0 - slip)
        den = num + (1.0 - L) * guess
    else:
        num = L * slip
        den = num + (1.0 - L) * (1.0 - guess)

    posterior = (num / den) if den > 0 else L
    posterior = clamp(posterior)
    return clamp(posterior + (1.0 - posterior) * transition)


def predict_success_prob(L: float, guess: float, slip: float) -> float:
    """
    Предсказание вероятности успешного выполенения действия
    """
    return clamp(clamp(L) * (1.0 - clamp(slip)) + (1.0 - clamp(L)) * clamp(guess))


def estimate_theme_level(request: PredictRequest, params: BKTParams) -> float:
    """
    Оценка уровня знания по теме.

    Используем:
    - mastery_coefficient по теме (если None -> params.prior)
    - среднее mastery по связанным темам (если есть)
    - время изучения темы
    - прогресс по теме (lesson_index / total_lessons)
    """
    theme = request.theme
    related = request.related_themes

    # base
    if getattr(theme, "mastery_coefficient", None) is not None:
        base = clamp(theme.mastery_coefficient)
    else:
        base = clamp(params.prior)

    # related themes
    if related:
        rel_masteries = []
        for t in related:
            mc = getattr(t, "mastery_coefficient", None)
            if mc is not None:
                rel_masteries.append(float(mc))
        if rel_masteries:
            rel_avg = sum(rel_masteries) / len(rel_masteries)
            W_RELATED = 0.2
            base = (1.0 - W_RELATED) * base + W_RELATED * clamp(rel_avg)

    # time spent (saturates at 10h)
    time_spent = getattr(theme, "time_spent", None)
    if time_spent is not None:
        norm = min(int(time_spent), 36000) / 36000.0
        TIME_ALPHA = 0.2
        base = clamp(base + TIME_ALPHA * (norm - 0.5))

    # progress
    total_lessons = getattr(request, "total_lessons", None)
    if total_lessons:
        progress = clamp(float(request.lesson_index) / float(total_lessons))
        W_PROGRESS = 0.2
        base = (1.0 - W_PROGRESS) * base + W_PROGRESS * progress

    return clamp(base)


def compute_prior(request: PredictRequest, params: BKTParams) -> float:
    """
    Оценка prior_L (вероятность знания до наблюдения).

    Идея (как было):
    - theme_level: глобальная оценка по теме
    - lesson_mastery: локальная оценка по уроку
    - чем больше наблюдений (attempts) по уроку, тем больше доверяем lesson_mastery
    """
    theme_level = estimate_theme_level(request, params)

    lesson_mastery = getattr(request, "lesson_mastery", None)
    if lesson_mastery is None:
        return clamp(theme_level)

    lesson_level = clamp(lesson_mastery)

    # attempts_done = action_index - 1
    attempts_done = max(0, int(getattr(request, "action_index", 1)) - 1)

    K = 10.0
    w_lesson = clamp(attempts_done / K)  # 0..1 after ~10 attempts
    w_theme = 1.0 - w_lesson

    return clamp(w_theme * theme_level + w_lesson * lesson_level)


def effective_guess_slip(action_difficulty: float, base_guess: float, base_slip: float) -> tuple[float, float]:
    """
    Адаптация guess/slip под конкретное действие.

    Идея: Чем сложнее действие, тем:
    - ниже шанс угадать не зная (guess уменьшается)
    - выше риск ошибиться даже зная (slip увеличивается).
    """
    d = clamp(action_difficulty, 0.1, 1.0)
    centered = d - 0.5
    SCALE = 0.6
    g = clamp(base_guess * (1.0 - SCALE * centered))
    s = clamp(base_slip  * (1.0 + SCALE * centered))
    return g, s


def choose_action_by_target(preds: List[dict], target_range: Tuple[float, float]) -> dict:
    low, high = target_range
    low, high = clamp(low), clamp(high)
    if low > high:
        low, high = high, low
    center = (low + high) / 2.0

    in_range = [p for p in preds if low <= p["success_prediction"] <= high]
    pool = in_range if in_range else preds
    return min(pool, key=lambda p: abs(p["success_prediction"] - center))


def predict_action(request: PredictRequest, target_success_range: Tuple[float, float] = (0.4, 0.6)) -> dict:
    params = get_params_from_env()
    prior_L = compute_prior(request, params)

    preds: List[dict] = []
    for a in request.actions:
        d = float(a.action_difficulty or 0.5)
        g, s = effective_guess_slip(d, params.guess, params.slip)
        p = predict_success_prob(prior_L, g, s)

        preds.append(
            {
                "action_id": int(a.action_id),
                "action_type": a.action_type,
                "action_difficulty": a.action_difficulty,
                "success_prediction": float(p),
                "effective_guess": float(g),
                "effective_slip": float(s),
                "prior_L": float(prior_L),
            }
        )

    chosen = choose_action_by_target(preds, target_success_range)
    return {
        "theme_id": request.theme.theme_id,
        "lesson_index": int(request.lesson_index),
        "action_index": int(request.action_index),
        "chosen_action": chosen,
        "actions": preds,
    }
