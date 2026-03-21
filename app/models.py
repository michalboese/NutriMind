from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class MealRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be blank or whitespace-only")
        return v


class MealRecord(BaseModel):
    id: int
    description: str
    meal_name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    created_at: datetime

    model_config = {"from_attributes": True}


class DailySummary(BaseModel):
    date: str
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    meal_count: int
