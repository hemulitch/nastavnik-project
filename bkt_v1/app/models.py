from typing import List
from pydantic import BaseModel, Field, confloat


class RelatedTheme(BaseModel):
    related_theme_id: str = Field(..., min_length=1)
    mastery_coefficient: confloat(ge=0.0, le=1.0)


class PredictRequest(BaseModel):
    theme_id: str = Field(..., min_length=1)
    related_themes: List[RelatedTheme] = Field(default_factory=list)


class PredictResponse(BaseModel):
    theme_id: str
    success_prediction: float
