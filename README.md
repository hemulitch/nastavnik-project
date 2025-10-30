# BKT 

### Run

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
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

```bash
$env:BKT_PARAMS_JSON = "\path\to\params.json" 
python -m uvicorn newapp.app.main:app --reload --port 8001

```
