import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.course import Course, StudentCourse, EducatorCourse, Semester
from app.models.student import Student
from app.models.educator import Educator
from app.models.relationship import EducatorStudent
from app.middleware.auth_middleware import get_current_user, require_role

router = APIRouter()


class CourseCreate(BaseModel):
    code: str
    title: str
    credit_units: int = 3
    level: Optional[str] = None
    department: Optional[str] = None
    faculty: Optional[str] = None
    semester: Optional[Semester] = None


class StudentCourseEnroll(BaseModel):
    course_id: str
    academic_session: str       # e.g. "2024/2025"
    semester: Semester


class EducatorCourseAssign(BaseModel):
    course_id: str
    academic_session: str
    semester: Semester


class ScoreUpdate(BaseModel):
    student_course_id: str
    score: float                # 0-100
    grade: Optional[str] = None


GRADE_MAP = [
    (70, "A", 5.0), (60, "B", 4.0), (50, "C", 3.0), (45, "D", 2.0), (0, "F", 0.0)
]

def _compute_grade(score: float) -> tuple[str, float]:
    for threshold, grade, point in GRADE_MAP:
        if score >= threshold:
            return grade, point
    return "F", 0.0


def _compute_gpa(db: Session, student_id: str) -> float | None:
    courses = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.grade_point != None,
        StudentCourse.is_active == True,
    ).all()
    if not courses:
        return None
    total_points = sum(c.grade_point * (c.course.credit_units if c.course else 3) for c in courses)
    total_units = sum(c.course.credit_units if c.course else 3 for c in courses)
    return round(total_points / total_units, 2) if total_units > 0 else None


# ── Course management (admin/educator) ────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a course")
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    existing = db.query(Course).filter(Course.code == payload.code.upper()).first()
    if existing:
        raise HTTPException(status_code=409, detail={"success": False, "message": f"Course {payload.code} already exists.", "code": "COURSE_EXISTS"})
    course = Course(id=str(uuid.uuid4()), **payload.model_dump(), code=payload.code.upper())
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"success": True, "message": "Course created.", "course": {"id": course.id, "code": course.code, "title": course.title}}


@router.get("/", summary="List all courses")
def list_courses(
    department: Optional[str] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Course).filter(Course.is_active == True)
    if department:
        query = query.filter(Course.department == department)
    if level:
        query = query.filter(Course.level == level)
    courses = query.all()
    return {
        "success": True,
        "count": len(courses),
        "courses": [{"id": c.id, "code": c.code, "title": c.title, "credit_units": c.credit_units, "level": c.level, "department": c.department, "semester": c.semester} for c in courses],
    }


# ── Student course enrollment ─────────────────────────────────────────────────

@router.post("/student/enroll", summary="Enroll student in courses")
def enroll_student(
    payload: StudentCourseEnroll,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Students enroll themselves; educators/admins can enroll any student."""
    student = db.query(Student).filter(Student.user_id == current_user["uid"]).first()
    if not student and current_user["role"] == "student":
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student profile not found.", "code": "NOT_FOUND"})

    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Course not found.", "code": "COURSE_NOT_FOUND"})

    # Prevent duplicate enrollment
    existing = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.course_id == payload.course_id,
        StudentCourse.academic_session == payload.academic_session,
        StudentCourse.semester == payload.semester,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail={"success": False, "message": "Already enrolled in this course.", "code": "ALREADY_ENROLLED"})

    enrollment = StudentCourse(
        id=str(uuid.uuid4()),
        student_id=student.id,
        course_id=payload.course_id,
        academic_session=payload.academic_session,
        semester=payload.semester,
    )
    db.add(enrollment)

    # Auto-link to any educator teaching this course in this session
    educator_courses = db.query(EducatorCourse).filter(
        EducatorCourse.course_id == payload.course_id,
        EducatorCourse.academic_session == payload.academic_session,
        EducatorCourse.semester == payload.semester,
    ).all()
    for ec in educator_courses:
        link_exists = db.query(EducatorStudent).filter(
            EducatorStudent.educator_id == ec.educator_id,
            EducatorStudent.student_id == student.id,
            EducatorStudent.course_id == payload.course_id,
        ).first()
        if not link_exists:
            db.add(EducatorStudent(
                id=str(uuid.uuid4()),
                educator_id=ec.educator_id,
                student_id=student.id,
                course_id=payload.course_id,
                academic_session=payload.academic_session,
            ))

    db.commit()
    return {"success": True, "message": f"Enrolled in {course.code} — {course.title}."}


@router.get("/student/my-courses", summary="Get my enrolled courses")
def my_courses(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.user_id == current_user["uid"]).first()
    if not student:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Student profile not found.", "code": "NOT_FOUND"})

    enrollments = db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.is_active == True,
    ).all()
    return {
        "success": True,
        "courses": [{
            "enrollment_id": e.id,
            "course_id": e.course_id,
            "code": e.course.code if e.course else None,
            "title": e.course.title if e.course else None,
            "credit_units": e.course.credit_units if e.course else None,
            "academic_session": e.academic_session,
            "semester": e.semester,
            "score": e.score,
            "grade": e.grade,
            "grade_point": e.grade_point,
        } for e in enrollments],
    }


# ── Educator course assignment ────────────────────────────────────────────────

@router.post("/educator/assign", summary="Assign educator to a course")
def assign_educator(
    payload: EducatorCourseAssign,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    educator = db.query(Educator).filter(Educator.user_id == current_user["uid"]).first()
    if not educator:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Educator profile not found.", "code": "NOT_FOUND"})
    if not educator.is_approved:
        raise HTTPException(status_code=403, detail={"success": False, "message": "Your account is pending admin approval.", "code": "PENDING_APPROVAL"})

    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Course not found.", "code": "COURSE_NOT_FOUND"})

    existing = db.query(EducatorCourse).filter(
        EducatorCourse.educator_id == educator.id,
        EducatorCourse.course_id == payload.course_id,
        EducatorCourse.academic_session == payload.academic_session,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail={"success": False, "message": "Already assigned to this course.", "code": "ALREADY_ASSIGNED"})

    ec = EducatorCourse(
        id=str(uuid.uuid4()),
        educator_id=educator.id,
        course_id=payload.course_id,
        academic_session=payload.academic_session,
        semester=payload.semester,
    )
    db.add(ec)

    # Auto-link to all students already enrolled in this course
    student_courses = db.query(StudentCourse).filter(
        StudentCourse.course_id == payload.course_id,
        StudentCourse.academic_session == payload.academic_session,
    ).all()
    for sc in student_courses:
        link_exists = db.query(EducatorStudent).filter(
            EducatorStudent.educator_id == educator.id,
            EducatorStudent.student_id == sc.student_id,
            EducatorStudent.course_id == payload.course_id,
        ).first()
        if not link_exists:
            db.add(EducatorStudent(
                id=str(uuid.uuid4()),
                educator_id=educator.id,
                student_id=sc.student_id,
                course_id=payload.course_id,
                academic_session=payload.academic_session,
            ))

    db.commit()
    return {"success": True, "message": f"Assigned to {course.code} — {course.title}. Student relationships created."}


@router.post("/educator/score", summary="Record student score for a course")
def record_score(
    payload: ScoreUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """Educator records a student's score — GPA is automatically recomputed."""
    enrollment = db.query(StudentCourse).filter(StudentCourse.id == payload.student_course_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Enrollment not found.", "code": "NOT_FOUND"})

    if not (0 <= payload.score <= 100):
        raise HTTPException(status_code=422, detail={"success": False, "message": "Score must be between 0 and 100.", "code": "INVALID_SCORE"})

    grade, grade_point = _compute_grade(payload.score)
    enrollment.score = payload.score
    enrollment.grade = payload.grade or grade
    enrollment.grade_point = grade_point

    # Recompute student GPA
    new_gpa = _compute_gpa(db, enrollment.student_id)
    student = db.query(Student).filter(Student.id == enrollment.student_id).first()
    if student and new_gpa is not None:
        student.gpa = new_gpa

    db.commit()
    return {
        "success": True,
        "message": "Score recorded and GPA updated.",
        "grade": grade,
        "grade_point": grade_point,
        "new_gpa": new_gpa,
    }
