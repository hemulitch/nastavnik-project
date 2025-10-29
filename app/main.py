from fastapi import FastAPI
from .models import PredictRequest, PredictResponse
from .bkt import TrainedParamsStore, predict_success

app = FastAPI(title="BKT Predictor")
store: TrainedParamsStore | None = TrainedParamsStore.from_env()


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    result = predict_success(payload.model_dump(), store)
    return PredictResponse(**result)