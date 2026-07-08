from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentUpdate, StudentResponse
from app.middleware.auth_middleware import get_current_user, require_role, resolve_student_id
from app.services.gemini_service import generate_student_insight
from app.services.cloudinary_service import upload_file

router = APIRouter()


@router.get("/", response_model=list[StudentResponse])
def list_students(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """Educators and admins can list all students."""
    return db.query(Student).all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: str = Depends(resolve_student_id),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Students can fetch their own profile (pass "me" as student_id);
    educators/admins can fetch any by real Student.id."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Students can only see themselves
    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    payload: StudentUpdate,
    student_id: str = Depends(resolve_student_id),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update student data and regenerate AI insight.
    Students can edit their own record (pass "me" as student_id);
    educators/admins can edit any student by real Student.id."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(student, field, value)

    # Regenerate AI insight whenever data changes
    student_data = {
        "gpa": student.gpa,
        "attendance_rate": student.attendance_rate,
        "grade_level": student.grade_level,
        "department": student.department,
    }
    student.ai_summary = await generate_student_insight(student_data)

    # Compute a simple risk score (extend this with your own logic)
    score = 0.0
    if student.gpa is not None and student.gpa < 2.0:
        score += 0.5
    if student.attendance_rate is not None and student.attendance_rate < 0.75:
        score += 0.5
    student.risk_score = min(score, 1.0)
    student.risk_label = (
        "critical" if score >= 1.0
        else "high" if score >= 0.7
        else "medium" if score >= 0.4
        else "low"
    )

    db.commit()
    db.refresh(student)
    return student


@router.post("/{student_id}/avatar")
def upload_avatar(
    student_id: str = Depends(resolve_student_id),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload or replace a student's avatar via Cloudinary.
    Students can upload their own (pass "me" as student_id);
    educators/admins can upload for any student by real Student.id."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = upload_file(
        file.file.read(),
        folder_key="avatar",
        public_id=f"student_{student_id}",
        resource_type="image",
    )

    # Update the User record's avatar_url
    user = db.query(User).filter(User.id == student.user_id).first()
    if user:
        user.avatar_url = result["url"]
        db.commit()

    return {"avatar_url": result["url"]}
