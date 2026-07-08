import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.reminder import Reminder, ReminderType
from app.models.student import Student
from app.models.user import User
from app.middleware.auth_middleware import get_current_user, require_role, resolve_student_id
from app.services.onesignal_service import send_push

router = APIRouter()


class ReminderCreate(BaseModel):
    student_id: str
    type: ReminderType = ReminderType.general
    title: str
    message: str
    due_date: Optional[str] = None    # ISO date string


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create and send a reminder")
async def create_reminder(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """Educator creates a reminder for a student. Push notification sent immediately."""
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student not found.", "code": "NOT_FOUND"})

    reminder = Reminder(
        id=str(uuid.uuid4()),
        student_id=payload.student_id,
        created_by=current_user["uid"],
        type=payload.type,
        title=payload.title,
        message=payload.message,
        due_date=datetime.fromisoformat(payload.due_date) if payload.due_date else None,
    )
    db.add(reminder)

    # Send push notification
    student_user = db.query(User).filter(User.id == student.user_id).first()
    sent = False
    if student_user and student_user.onesignal_player_id:
        await send_push(
            player_ids=[student_user.onesignal_player_id],
            title=f"📌 {payload.title}",
            message=payload.message,
            data={"type": "reminder", "reminder_id": reminder.id, "reminder_type": payload.type.value}
        )
        reminder.is_sent = True
        reminder.sent_at = datetime.now(timezone.utc)
        sent = True

    db.commit()
    return {
        "success": True,
        "message": "Reminder created" + (" and sent." if sent else " but student has no device token."),
        "reminder_id": reminder.id,
        "push_sent": sent,
    }


@router.get("/student/{student_id}", summary="Get reminders for a student")
def student_reminders(
    student_id: str = Depends(resolve_student_id),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student not found.", "code": "NOT_FOUND"})

    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail={"success": False, "message": "Access denied.", "code": "ACCESS_DENIED"})

    reminders = db.query(Reminder).filter(
        Reminder.student_id == student_id
    ).order_by(Reminder.created_at.desc()).all()

    return {
        "success": True,
        "count": len(reminders),
        "reminders": [{
            "id": r.id,
            "type": r.type,
            "title": r.title,
            "message": r.message,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "is_read": r.is_read,
            "is_sent": r.is_sent,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reminders],
    }


@router.patch("/{reminder_id}/read", summary="Mark reminder as read")
def mark_read(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Reminder not found.", "code": "NOT_FOUND"})
    reminder.is_read = True
    db.commit()
    return {"success": True, "message": "Reminder marked as read."}
