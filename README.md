# BKT 

### Run

```
pip install -r newapp/requirements.txt
python -m uvicorn newapp.app.main:app --reload --port 8001
```

Open docs: `http://127.0.0.1:8001/docs`

### Request

```json
{
  "theme_id": "math_004",
  "related_themes": [
    { "related_theme_id": "math_002", "mastery_coefficient": 0.85 },
    { "related_theme_id": "math_003", "mastery_coefficient": 0.72 }
  ]
}
```

### Configure trained pyBKT model params

- Provide a JSON file via env var `BKT_PARAMS_JSON`:

```json
{
  "math_004": {"transition": 0.15, "guess": 0.20, "slip": 0.10, "prior": 0.10}
}
```

```bash
$env:BKT_PARAMS_JSON = "\path\to\params.json" 
python -m uvicorn newapp.app.main:app --reload --port 8001
```