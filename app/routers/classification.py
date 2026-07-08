import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.student import Student
from app.models.educator import Educator
from app.models.relationship import EducatorStudent
from app.models.ai_classification import AIClassification
from app.models.user import User
from app.middleware.auth_middleware import get_current_user, require_role
from app.services.gemini_service import classify_student
from app.services.onesignal_service import send_push

router = APIRouter()


def _student_dict(student: Student, db: Session) -> dict:
    from app.models.course import StudentCourse
    course_count = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.is_active == True,
    ).count()
    return {
        "gpa": student.gpa,
        "attendance_rate": student.attendance_rate,
        "level": student.level,
        "department": student.department,
        "programme": student.programme,
        "course_count": course_count,
    }


async def _run_classification(student: Student, db: Session, triggered_by: str = "system"):
    """Core classification logic — callable from background tasks or directly."""
    student_dict = _student_dict(student, db)
    result = await classify_student(student_dict, triggered_by)

    classification = AIClassification(
        id=str(uuid.uuid4()),
        student_id=student.id,
        gpa_at_time=student.gpa,
        attendance_at_time=student.attendance_rate,
        **result,
    )
    db.add(classification)

    # Update student's current risk label
    student.risk_label = result["risk_label"]
    student.risk_score = result["risk_score"]
    student.ai_summary = result["summary"]
    db.commit()

    # Alert educators if critical or at-risk
    if result["risk_label"] in ("critical", "at_risk") and result.get("educator_alert"):
        relationships = db.query(EducatorStudent).filter(
            EducatorStudent.student_id == student.id
        ).all()
        for rel in relationships:
            educator = db.query(Educator).filter(Educator.id == rel.educator_id).first()
            if educator:
                educator_user = db.query(User).filter(User.id == educator.user_id).first()
                if educator_user and educator_user.onesignal_player_id:
                    student_user = db.query(User).filter(User.id == student.user_id).first()
                    await send_push(
                        player_ids=[educator_user.onesignal_player_id],
                        title="⚠️ Student alert",
                        message=result["educator_alert"],
                        data={
                            "type": "student_alert",
                            "student_id": student.id,
                            "risk_label": result["risk_label"],
                            "student_name": student_user.full_name if student_user else "",
                        }
                    )

    return result


@router.post("/classify/{student_id}", summary="Run AI classification for a student")
async def classify(
    student_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Runs Gemini AI classification for a student.
    Students can classify themselves; educators can classify their students.
    Returns the classification result immediately.
    Educator alerts are dispatched in the background.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student not found.", "code": "NOT_FOUND"})

    # Access control
    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail={"success": False, "message": "Access denied.", "code": "ACCESS_DENIED"})

    result = await _run_classification(student, db, triggered_by=current_user["role"])

    return {
        "success": True,
        "message": "Classification complete.",
        "classification": {
            "risk_label": result["risk_label"],
            "risk_score": result["risk_score"],
            "gpa_grade": result.get("gpa_grade"),
            "summary": result["summary"],
            "remarks": result["remarks"],
            "recommendations": result["recommendations"],
            "educator_alert": result.get("educator_alert"),
            "model_used": result["model_used"],
        }
    }


@router.get("/history/{student_id}", summary="Get classification history for a student")
def classification_history(
    student_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student not found.", "code": "NOT_FOUND"})

    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail={"success": False, "message": "Access denied.", "code": "ACCESS_DENIED"})

    history = (
        db.query(AIClassification)
        .filter(AIClassification.student_id == student_id)
        .order_by(AIClassification.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "count": len(history),
        "history": [{
            "id": h.id,
            "risk_label": h.risk_label,
            "risk_score": h.risk_score,
            "gpa_at_time": h.gpa_at_time,
            "gpa_grade": h.gpa_grade,
            "summary": h.summary,
            "remarks": h.remarks,
            "recommendations": h.recommendations,
            "model_used": h.model_used,
            "triggered_by": h.triggered_by,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        } for h in history],
    }
