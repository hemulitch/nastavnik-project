from typing import List, Optional
from pydantic import BaseModel, Field, confloat, conint


class Theme(BaseModel):
    theme_id: str = Field(..., min_length=1)
    mastery_coefficient: confloat(ge=0.0, le=1.0)
    time_spent: Optional[conint(ge=0)] = None


class PredictRequest(BaseModel):
    theme: Theme
    related_themes: List[Theme] = Field(default_factory=list)

    lesson_index: conint(ge=1)
    lesson_mastery: Optional[confloat(ge=0.0, le=1.0)] = None
    total_lessons: Optional[conint(ge=1)] = None

    action_index: conint(ge=1)
    action_type: Optional[str] = Field(default=None, min_length=1)
    action_difficulty: Optional[float] = Field(default=None, ge=0.1, le=1.0, multiple_of=0.1)


class PredictResponse(BaseModel):
    theme_id: str
    lesson_index: int
    action_index: int
    success_prediction: confloat(ge=0.0, le=1.0)
