import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.goal import Goal
from app.models.student import Student
from app.models.intervention import Intervention, InterventionType
from app.schemas.goal import GoalCreate, GoalResponse
from app.middleware.auth_middleware import get_current_user, require_role
from app.services.gemini_service import recommend_academic_interventions

router = APIRouter()


@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, summary="Describe a goal and get AI-recommended academic interventions")
async def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("student")),
):
    """
    A student describes a personal goal. The AI recommends concrete academic-success
    interventions toward it, and each recommendation is saved as a real Intervention
    record — same as one an educator would raise — so the student's educator sees it
    via the existing interventions endpoints. Goals unrelated to academics are saved
    for the record but produce no interventions.
    """
    student = db.query(Student).filter(Student.user_id == current_user["uid"]).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "No student profile found for this account.", "code": "STUDENT_NOT_FOUND"},
        )

    student_data = {
        "gpa": student.gpa,
        "attendance_rate": student.attendance_rate,
        "level": student.level,
        "department": student.department,
        "risk_label": student.risk_label,
    }

    result = await recommend_academic_interventions(student_data, payload.description)

    ai_summary = result["summary"]
    if result["out_of_scope"] and not ai_summary:
        ai_summary = (
            "This goal doesn't look academic-related, so no interventions were created. "
            "Try describing a goal about coursework, study habits, or academic performance."
        )

    goal = Goal(
        id=str(uuid.uuid4()),
        student_id=student.id,
        description=payload.description,
        ai_summary=ai_summary,
    )
    db.add(goal)
    db.flush()   # goal.id needed for the interventions' FK before commit

    for item in result["interventions"]:
        title = (item.get("title") or "Academic support")[:255]
        description = item.get("description")
        db.add(Intervention(
            id=str(uuid.uuid4()),
            student_id=student.id,
            raised_by=current_user["uid"],
            type=InterventionType.academic,
            title=title,
            description=description,
            ai_recommendation=description,
            goal_id=goal.id,
        ))

    db.commit()
    db.refresh(goal)
    return goal


@router.get("/", response_model=list[GoalResponse], summary="List goals")
def list_goals(
    student_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Students see their own goals. Educators/admins can filter by student_id (or see all)."""
    if current_user["role"] == "student":
        student = db.query(Student).filter(Student.user_id == current_user["uid"]).first()
        if not student:
            return []
        query = db.query(Goal).filter(Goal.student_id == student.id)
    else:
        query = db.query(Goal)
        if student_id:
            query = query.filter(Goal.student_id == student_id)

    return query.order_by(Goal.created_at.desc()).all()


@router.get("/{goal_id}", response_model=GoalResponse, summary="Get a single goal")
def get_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Goal not found.", "code": "NOT_FOUND"},
        )

    if current_user["role"] == "student":
        student = db.query(Student).filter(Student.user_id == current_user["uid"]).first()
        if not student or goal.student_id != student.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Access denied.", "code": "ACCESS_DENIED"},
            )

    return goal
