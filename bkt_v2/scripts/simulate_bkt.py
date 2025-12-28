import argparse
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(x)))


def utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def post_json(url: str, payload: Dict[str, Any], timeout_s: float = 10.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        raise RuntimeError(f"HTTP {e.code} from {url}: {err_body}") from e
    except URLError as e:
        raise RuntimeError(f"Cannot reach {url}: {e}") from e


def wait_for_server(base_url: str, retries: int = 80, sleep_s: float = 0.2) -> None:
    base = base_url.rstrip("/")
    url = base + "/health"
    last_err: Optional[Exception] = None
    for _ in range(retries):
        try:
            req = Request(url=url, headers={"Accept": "application/json"}, method="GET")
            with urlopen(req, timeout=2.0) as resp:
                raw = resp.read().decode("utf-8")
                if resp.status == 200 and raw:
                    return
        except Exception as e:
            last_err = e
        time.sleep(sleep_s)
    raise RuntimeError(f"Server not ready at {base_url}. Last error: {last_err}")


@dataclass
class TrackLesson:
    mastery_target: float
    max_actions: int  


@dataclass
class StudentState:
    engagement_prob: float
    theme_id: str
    theme_mastery: float
    theme_time_spent_s: int
    related_themes: List[Dict[str, Any]]
    lesson_index: int
    total_lessons: int
    lesson_mastery: float
    action_index: int  


ACTION_TYPES: Tuple[str, ...] = ("test", "practice", "article", "video", "hint")


def generate_actions(rng: random.Random, n: int = 6) -> List[Dict[str, Any]]:
    def diff() -> float:
        return rng.choice([i / 10 for i in range(1, 11)])
    return [
        {"action_id": i + 1, "action_type": rng.choice(ACTION_TYPES), "action_difficulty": float(diff())}
        for i in range(n)
    ]


def generate_track(rng: random.Random, total_lessons: int = 10) -> List[TrackLesson]:
    return [
        TrackLesson(mastery_target=rng.uniform(0.85, 0.95), max_actions=rng.randint(10, 16))
        for _ in range(total_lessons)
    ]


def step_minutes(action_type: str, difficulty: float) -> int:
    base = {"hint": 2, "article": 6, "video": 8, "practice": 7, "test": 10}.get(action_type, 6)
    return int(base + round(4 * float(difficulty)))


def build_predict_payload(student: StudentState, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "theme": {
            "theme_id": student.theme_id,
            "mastery_coefficient": float(round(student.theme_mastery, 3)),
            "time_spent": int(student.theme_time_spent_s),
        },
        "related_themes": student.related_themes,
        "lesson_index": int(student.lesson_index),
        "lesson_mastery": float(round(student.lesson_mastery, 3)),
        "total_lessons": int(student.total_lessons),
        "action_index": int(student.action_index),
        "actions": actions,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8001")
    p.add_argument("--iter-limit", type=int, default=100)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--log-jsonl", default=None)
    p.add_argument("--transition", type=float, default=0.05)

    p.add_argument("--min-actions-per-lesson", type=int, default=8)

    args = p.parse_args()

    rng = random.Random(args.seed)
    wait_for_server(args.base_url)

    predict_url = args.base_url.rstrip("/") + "/predict"
    observe_url = args.base_url.rstrip("/") + "/observe"

    total_lessons = 10
    track = generate_track(rng, total_lessons=total_lessons)

    student = StudentState(
        engagement_prob=rng.uniform(0.85, 0.98),
        theme_id=f"theme_{rng.randint(1, 999):03d}",
        theme_mastery=rng.uniform(0.05, 0.20),
        theme_time_spent_s=0,
        related_themes=[
            {
                "theme_id": f"rel_{rng.randint(1, 999):03d}",
                "mastery_coefficient": float(round(rng.uniform(0.1, 0.95), 3)),
                "time_spent": int(rng.randint(0, 14400)),
            }
            for _ in range(rng.randint(2, 4))
        ],
        lesson_index=1,
        total_lessons=total_lessons,
        lesson_mastery=rng.uniform(0.0, 0.15),
        action_index=1, 
    )

    jsonl_fp = None
    if args.log_jsonl:
        ensure_parent_dir(args.log_jsonl)
        jsonl_fp = open(args.log_jsonl, "w", encoding="utf-8")

    def write_jsonl(obj: Dict[str, Any]) -> None:
        if not jsonl_fp:
            return
        jsonl_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
        jsonl_fp.flush()

    write_jsonl({"event_type": "run_start", "ts": utc_ts(), "seed": args.seed})

    completed_lessons = 0

    for it in range(1, args.iter_limit + 1):
        if student.lesson_index > student.total_lessons:
            break

        current = track[student.lesson_index - 1]

        actions = generate_actions(rng, n=6)
        attempts_done_pre = student.action_index - 1

        pre = {
            "lesson_index": student.lesson_index,
            "action_index": student.action_index,
            "attempts_done": attempts_done_pre,
            "lesson_mastery": round(student.lesson_mastery, 6),
            "theme_mastery": round(student.theme_mastery, 6),
        }

        pred = post_json(predict_url, build_predict_payload(student, actions))
        chosen = pred.get("chosen_action") or {}

        # симуляция студента
        attempted = rng.random() <= student.engagement_prob
        success = None
        p_success = None
        minutes_spent = 0

        if attempted:
            student.action_index += 1

            p_success = clamp(float(chosen.get("success_prediction", 0.5)))
            # немного шума, чтобы не было идеала
            p_success = clamp(p_success + rng.uniform(-0.10, 0.10))
            success = rng.random() < p_success

            minutes_spent = step_minutes(
                chosen.get("action_type") or "practice",
                float(chosen.get("action_difficulty") or 0.5),
            )
            student.theme_time_spent_s += minutes_spent * 60

            obs_payload = {
                "attempted": True,
                "correct": bool(success),
                "prior_L": float(chosen["prior_L"]),
                "effective_guess": float(chosen["effective_guess"]),
                "effective_slip": float(chosen["effective_slip"]),
                "transition": float(args.transition),
            }
            upd = post_json(observe_url, obs_payload)
            updated_L = float(upd["updated_L"])

            student.lesson_mastery = updated_L
            student.theme_mastery = clamp(0.92 * student.theme_mastery + 0.08 * student.lesson_mastery)
        else:
            pass

        attempts_done_post = student.action_index - 1

        lesson_done = (
            (student.lesson_mastery >= current.mastery_target and attempts_done_post >= args.min_actions_per_lesson)
            or (attempts_done_post >= current.max_actions)
        )

        post = {
            "lesson_index": student.lesson_index,
            "action_index": student.action_index,
            "attempts_done": attempts_done_post,
            "lesson_mastery": round(student.lesson_mastery, 6),
            "theme_mastery": round(student.theme_mastery, 6),
        }

        if args.verbose:
            print(
                f"[{it:03d}] lesson={pre['lesson_index']} "
                f"attempts={post['attempts_done']} lesson_mastery={post['lesson_mastery']:.3f} "
                f"lesson_target={current.mastery_target:.2f} "
                f"chosen={chosen.get('action_id')} attempted={attempted} success={success} p={p_success} done={lesson_done} "
                f"theme_mastery={post['theme_mastery']:.3f} "
            )

        write_jsonl(
            {
                "event_type": "step",
                "ts": utc_ts(),
                "iteration": it,
                "pre": pre,
                "chosen_action": chosen,
                "attempted": attempted,
                "success": success,
                "p_success": p_success,
                "minutes_spent": minutes_spent,
                "post": post,
                "lesson_done": lesson_done,
            }
        )

        if lesson_done:
            completed_lessons += 1
            student.lesson_index += 1

            student.action_index = 1  

            student.lesson_mastery = clamp(student.theme_mastery + rng.uniform(-0.15, 0.10))

    done = student.lesson_index > student.total_lessons
    write_jsonl({"event_type": "summary", "ts": utc_ts(), "done": done, "lessons_completed": completed_lessons})

    if jsonl_fp:
        jsonl_fp.close()

    print("\n=== SUMMARY ===")
    print(f"done={done} lessons_completed={completed_lessons}/{total_lessons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
