from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.student import Student
from app.models.educator import Educator
from app.models.relationship import EducatorStudent
from app.models.intervention import Intervention
from app.models.ai_classification import AIClassification
from app.models.course import StudentCourse
from app.middleware.auth_middleware import get_current_user, require_role, resolve_student_id
from app.services.gemini_service import generate_analytics_summary

router = APIRouter()

RISK_ORDER = ["critical", "at_risk", "average", "on_track", "high_potential", "unclassified"]


@router.get("/student/{student_id}", summary="Student analytics dashboard")
async def student_analytics(
    student_id: str = Depends(resolve_student_id),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Full analytics for a single student — GPA trend, classification history, course performance.
    Students can view their own (pass "me" as student_id); educators/admins use the real Student.id."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student not found.", "code": "NOT_FOUND"})

    if current_user["role"] == "student" and student.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail={"success": False, "message": "Access denied.", "code": "ACCESS_DENIED"})

    # GPA trend from classification history
    classifications = (
        db.query(AIClassification)
        .filter(AIClassification.student_id == student_id)
        .order_by(AIClassification.created_at.asc())
        .all()
    )

    gpa_trend = [
        {"date": c.created_at.isoformat(), "gpa": c.gpa_at_time, "risk_label": c.risk_label}
        for c in classifications if c.gpa_at_time is not None
    ]

    # Course performance
    courses = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.is_active == True,
    ).all()
    course_performance = [{
        "code": c.course.code if c.course else None,
        "title": c.course.title if c.course else None,
        "credit_units": c.course.credit_units if c.course else None,
        "score": c.score,
        "grade": c.grade,
        "grade_point": c.grade_point,
        "semester": c.semester,
        "session": c.academic_session,
    } for c in courses]

    # Interventions summary
    interventions = db.query(Intervention).filter(Intervention.student_id == student_id).all()
    intervention_summary = {
        "total": len(interventions),
        "open": sum(1 for i in interventions if i.status.value == "open"),
        "resolved": sum(1 for i in interventions if i.status.value == "resolved"),
    }

    latest = classifications[-1] if classifications else None

    return {
        "success": True,
        "student_id": student_id,
        "current": {
            "gpa": student.gpa,
            "attendance_rate": student.attendance_rate,
            "risk_label": student.risk_label,
            "risk_score": student.risk_score,
            "ai_summary": student.ai_summary,
        },
        "gpa_trend": gpa_trend,
        "course_performance": course_performance,
        "interventions": intervention_summary,
        "latest_remarks": latest.remarks if latest else None,
        "latest_recommendations": latest.recommendations if latest else [],
    }


@router.get("/educator/cohort", summary="Educator cohort analytics")
async def educator_cohort_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """
    Full cohort analytics for an educator — all their linked students
    broken down by risk label, GPA distribution, and intervention stats.
    Includes a Gemini-generated natural language summary.
    """
    educator = db.query(Educator).filter(Educator.user_id == current_user["uid"]).first()
    if not educator:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Educator profile not found.", "code": "NOT_FOUND"})

    # Get all linked students
    relationships = db.query(EducatorStudent).filter(
        EducatorStudent.educator_id == educator.id,
        EducatorStudent.status == "active",
    ).all()
    student_ids = list({r.student_id for r in relationships})

    if not student_ids:
        return {
            "success": True,
            "message": "No students linked yet.",
            "total_students": 0,
            "breakdown": {},
            "ai_summary": "No students are linked to your account yet. Assign courses to begin.",
        }

    students = db.query(Student).filter(Student.id.in_(student_ids)).all()

    # Risk breakdown
    breakdown = {label: 0 for label in RISK_ORDER}
    gpa_list = []
    for s in students:
        label = s.risk_label or "unclassified"
        breakdown[label] = breakdown.get(label, 0) + 1
        if s.gpa is not None:
            gpa_list.append(s.gpa)

    avg_gpa = round(sum(gpa_list) / len(gpa_list), 2) if gpa_list else None

    # Intervention stats
    interventions = db.query(Intervention).filter(
        Intervention.student_id.in_(student_ids)
    ).all()
    intervention_stats = {
        "total": len(interventions),
        "open": sum(1 for i in interventions if i.status.value == "open"),
        "resolved": sum(1 for i in interventions if i.status.value == "resolved"),
        "escalated": sum(1 for i in interventions if i.status.value == "escalated"),
    }

    # Students needing urgent attention
    urgent = [
        {"student_id": s.id, "risk_label": s.risk_label, "gpa": s.gpa, "ai_summary": s.ai_summary}
        for s in students if s.risk_label in ("critical", "at_risk")
    ]

    cohort_data = {
        "total_students": len(students),
        "average_gpa": avg_gpa,
        "risk_breakdown": breakdown,
        "interventions": intervention_stats,
        "urgent_count": len(urgent),
    }

    ai_summary = await generate_analytics_summary(cohort_data)

    return {
        "success": True,
        "total_students": len(students),
        "average_gpa": avg_gpa,
        "risk_breakdown": {k: v for k, v in breakdown.items() if v > 0},
        "intervention_stats": intervention_stats,
        "urgent_students": urgent,
        "ai_summary": ai_summary,
    }
