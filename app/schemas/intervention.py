from pydantic import BaseModel
from typing import Optional
from app.models.intervention import InterventionType, InterventionStatus


class InterventionCreate(BaseModel):
    student_id: str
    type: InterventionType
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None


class InterventionUpdate(BaseModel):
    status: Optional[InterventionStatus] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None


class InterventionResponse(BaseModel):
    id: str
    student_id: str
    raised_by: str
    assigned_to: Optional[str]
    type: InterventionType
    status: InterventionStatus
    title: str
    description: Optional[str]
    ai_recommendation: Optional[str]
    attachment_url: Optional[str]

    class Config:
        from_attributes = True
