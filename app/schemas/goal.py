from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.models.intervention import InterventionStatus


class GoalCreate(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Goal description cannot be blank")
        return v.strip()


class GoalInterventionSummary(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: InterventionStatus

    class Config:
        from_attributes = True


class GoalResponse(BaseModel):
    id: str
    student_id: str
    description: str
    ai_summary: Optional[str]
    created_at: Optional[datetime]
    interventions: list[GoalInterventionSummary] = []

    class Config:
        from_attributes = True
