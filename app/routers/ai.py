from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.middleware.auth_middleware import get_current_user, require_role, resolve_student_id
from app.services.gemini_service import generate_student_insight, educator_chat

router = APIRouter()


class ChatMessage(BaseModel):
    role: str    # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    student_id: str
    conversation: list[ChatMessage]


@router.get("/insight/{student_id}")
async def get_student_insight(
    student_id: str = Depends(resolve_student_id),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a freshly generated AI insight for a student.
    Students can request their own insight (pass "me" as student_id);
    educators can request any by real Student.id.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")

    student_data = {
        "gpa": student.gpa,
        "attendance_rate": student.attendance_rate,
        "grade_level": student.grade_level,
        "department": student.department,
        "risk_score": student.risk_score,
        "risk_label": student.risk_label,
    }

    insight = await generate_student_insight(student_data)

    # Persist the latest insight on the student record
    student.ai_summary = insight
    db.commit()

    return {"student_id": student_id, "insight": insight}


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """
    Multi-turn AI chat for educators about a specific student.
    Flutter sends the full conversation history with each request.
    """
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Prepend student context to the conversation
    context_message = {
        "role": "user",
        "content": (
            f"Context: I am an educator asking about student {payload.student_id}. "
            f"Their profile: GPA={student.gpa}, attendance={student.attendance_rate}, "
            f"grade={student.grade_level}, risk={student.risk_label}."
        ),
    }

    conversation = [context_message] + [m.model_dump() for m in payload.conversation]
    reply = await educator_chat(conversation)

    return {"reply": reply}
