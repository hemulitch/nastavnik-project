from fastapi import FastAPI

from app.models import PredictRequest, PredictResponse, ObserveRequest, ObserveResponse
from app.bkt import predict_action, bkt_update

app = FastAPI(title="BKT Predictor")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    return PredictResponse(**predict_action(request))


@app.post("/observe", response_model=ObserveResponse)
def observe(req: ObserveRequest) -> ObserveResponse:
    if not req.attempted:
        # нет наблюдения -> знание не обновляем
        return ObserveResponse(updated_L=req.prior_L)

    if req.correct is None:
        # на всякий случай
        return ObserveResponse(updated_L=req.prior_L)

    updated = bkt_update(
        L=req.prior_L,
        guess=req.effective_guess,
        slip=req.effective_slip,
        transition=req.transition,
        correct=bool(req.correct),
    )
    return ObserveResponse(updated_L=updated)
