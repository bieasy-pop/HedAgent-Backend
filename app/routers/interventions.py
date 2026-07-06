import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intervention import Intervention, InterventionStatus
from app.models.student import Student
from app.models.user import User
from app.schemas.intervention import InterventionCreate, InterventionUpdate, InterventionResponse
from app.middleware.auth_middleware import get_current_user, require_role
from app.services.openai_service import generate_intervention_plan
from app.services.cloudinary_service import upload_file
from app.services.onesignal_service import send_push

router = APIRouter()


@router.get("/", response_model=list[InterventionResponse])
def list_interventions(
    student_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """List interventions, optionally filtered by student."""
    query = db.query(Intervention)
    if student_id:
        query = query.filter(Intervention.student_id == student_id)
    return query.order_by(Intervention.created_at.desc()).all()


@router.post("/", response_model=InterventionResponse, status_code=status.HTTP_201_CREATED)
async def create_intervention(
    payload: InterventionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """
    Raises a new intervention for a student.
    Automatically generates an AI action plan and notifies the assigned educator.
    """
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student_data = {
        "gpa": student.gpa,
        "attendance_rate": student.attendance_rate,
        "grade_level": student.grade_level,
        "risk_score": student.risk_score,
    }

    ai_plan = await generate_intervention_plan(
        student_data=student_data,
        intervention_type=payload.type.value,
        description=payload.description or "",
    )

    intervention = Intervention(
        id=str(uuid.uuid4()),
        student_id=payload.student_id,
        raised_by=current_user["uid"],
        assigned_to=payload.assigned_to,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        ai_recommendation=ai_plan,
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)

    # Notify the assigned educator if one is specified
    if payload.assigned_to:
        assignee = db.query(User).filter(User.id == payload.assigned_to).first()
        if assignee and assignee.onesignal_player_id:
            await send_push(
                player_ids=[assignee.onesignal_player_id],
                title="New intervention assigned",
                message=f"{payload.title} — {payload.type.value}",
                data={"intervention_id": intervention.id, "student_id": payload.student_id},
            )

    return intervention


@router.patch("/{intervention_id}", response_model=InterventionResponse)
def update_intervention(
    intervention_id: str,
    payload: InterventionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """Update status or reassign an intervention."""
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(intervention, field, value)

    if payload.status == InterventionStatus.resolved:
        intervention.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(intervention)
    return intervention


@router.post("/{intervention_id}/attachment")
def upload_attachment(
    intervention_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """Attach a document or image to an intervention via Cloudinary."""
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    result = upload_file(file.file.read(), folder_key="attachment")
    intervention.attachment_url = result["url"]
    db.commit()

    return {"attachment_url": result["url"]}
