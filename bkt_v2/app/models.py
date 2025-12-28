from typing import List, Optional
from pydantic import BaseModel, Field, confloat, conint


class Theme(BaseModel):
    theme_id: str = Field(..., min_length=1)
    mastery_coefficient: confloat(ge=0.0, le=1.0)
    time_spent: Optional[conint(ge=0)] = None


class RelatedTheme(BaseModel):
    theme_id: str = Field(..., min_length=1)
    mastery_coefficient: confloat(ge=0.0, le=1.0)
    time_spent: Optional[conint(ge=0)] = None


class Action(BaseModel):
    action_id: conint(ge=1)
    action_type: Optional[str] = Field(default=None, min_length=1)
    action_difficulty: Optional[float] = Field(default=None, ge=0.1, le=1.0)


class PredictRequest(BaseModel):
    theme: Theme
    related_themes: List[RelatedTheme] = Field(default_factory=list)
    lesson_index: conint(ge=1)
    lesson_mastery: confloat(ge=0.0, le=1.0)
    total_lessons: conint(ge=1)
    action_index: conint(ge=1) 
    actions: List[Action] = Field(..., min_items=1)


class ActionPrediction(BaseModel):
    action_id: int
    action_type: Optional[str]
    action_difficulty: Optional[float]
    success_prediction: confloat(ge=0.0, le=1.0)
    effective_guess: confloat(ge=0.0, le=1.0)
    effective_slip: confloat(ge=0.0, le=1.0)
    prior_L: confloat(ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    theme_id: str
    lesson_index: int
    action_index: int
    chosen_action: ActionPrediction
    actions: List[ActionPrediction]


class ObserveRequest(BaseModel):
    attempted: bool
    correct: Optional[bool] = None 
    prior_L: confloat(ge=0.0, le=1.0)
    effective_guess: confloat(ge=0.0, le=1.0)
    effective_slip: confloat(ge=0.0, le=1.0)
    transition: confloat(ge=0.0, le=1.0) = 0.15


class ObserveResponse(BaseModel):
    updated_L: confloat(ge=0.0, le=1.0)
