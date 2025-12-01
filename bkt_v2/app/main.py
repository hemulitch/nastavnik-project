from fastapi import FastAPI
from .models import PredictRequest, PredictResponse
from .bkt import predict_action

app = FastAPI(title="BKT Predictor")

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    result = predict_action(request)
    return PredictResponse(**result)
