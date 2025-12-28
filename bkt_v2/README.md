# BKT 

### Run

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```
Open docs: `http://127.0.0.1:8001/docs`

### Run simulation
From the project root (with API already running):
```
python scripts/simulate_bkt.py \
  --base-url http://127.0.0.1:8001 \
  --iter-limit 100 \
  --min-actions-per-lesson 8 \
  --seed 1 \
  --verbose \
  --log-jsonl logs/run.jsonl
```

### Request

```json
{
  "theme": {
    "theme_id": "math_004",
    "mastery_coefficient": 0.76,
    "time_spent": 3600
  },
  "related_themes": [
    {
      "theme_id": "math_002",
      "mastery_coefficient": 0.85,
      "time_spent": 7200
    },
    {
      "theme_id": "math_003",
      "mastery_coefficient": 0.72,
      "time_spent": 3600
    }
  ],
  "lesson_index": 3,
  "lesson_mastery": 0.65,
  "total_lessons": 10,
  "action_index": 5,
  "actions": [
    {
      "action_id": 1,
      "action_type": "test",
      "action_difficulty": 0.5
    },
    {
      "action_id": 2,
      "action_type": "article",
      "action_difficulty": 0.8
    }
  ]
}
```
