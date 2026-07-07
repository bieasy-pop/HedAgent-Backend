from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class Semester(str, enum.Enum):
    first = "first"
    second = "second"
    summer = "summer"


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True)
    code = Column(String, unique=True, nullable=False, index=True)   # e.g. "CSC301"
    title = Column(String, nullable=False)
    credit_units = Column(Integer, default=3)
    level = Column(String, nullable=True)                             # "100", "200", "300"
    department = Column(String, nullable=True)
    faculty = Column(String, nullable=True)
    semester = Column(Enum(Semester), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student_enrollments = relationship("StudentCourse", back_populates="course")
    educator_assignments = relationship("EducatorCourse", back_populates="course")


class StudentCourse(Base):
    """A student's enrolled courses for a given session."""
    __tablename__ = "student_courses"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    academic_session = Column(String, nullable=False)    # e.g. "2024/2025"
    semester = Column(Enum(Semester), nullable=False)
    score = Column(Float, nullable=True)                  # 0-100, updated by educator
    grade = Column(String, nullable=True)                 # A, B, C, D, F
    grade_point = Column(Float, nullable=True)            # 5.0, 4.0, 3.0 etc.
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student = relationship("Student", back_populates="courses")
    course = relationship("Course", back_populates="student_enrollments")


class EducatorCourse(Base):
    """Courses an educator is assigned to teach."""
    __tablename__ = "educator_courses"

    id = Column(String, primary_key=True)
    educator_id = Column(String, ForeignKey("educators.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    academic_session = Column(String, nullable=False)
    semester = Column(Enum(Semester), nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    educator = relationship("Educator", back_populates="courses")
    course = relationship("Course", back_populates="educator_assignments")
