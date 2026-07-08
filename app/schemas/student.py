from pydantic import BaseModel
from typing import Optional


class StudentUpdate(BaseModel):
    level: Optional[str] = None
    department: Optional[str] = None
    gpa: Optional[float] = None
    attendance_rate: Optional[float] = None
    student_number: Optional[str] = None
    meta: Optional[dict] = None


class StudentResponse(BaseModel):
    id: str
    user_id: str
    student_number: Optional[str]
    level: Optional[str]
    department: Optional[str]
    gpa: Optional[float]
    attendance_rate: Optional[float]
    risk_score: float
    risk_label: str
    ai_summary: Optional[str]

    class Config:
        from_attributes = True
