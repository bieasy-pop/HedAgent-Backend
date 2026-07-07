from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class RelationshipStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class EducatorStudent(Base):
    """
    Links an educator to a student based on shared courses/department/level.
    Created automatically when a student enrolls in a course taught by an educator.
    Can also be created manually by an educator or admin.
    """
    __tablename__ = "educator_students"

    id = Column(String, primary_key=True)
    educator_id = Column(String, ForeignKey("educators.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=True)   # shared course
    academic_session = Column(String, nullable=True)
    status = Column(Enum(RelationshipStatus), default=RelationshipStatus.active)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    educator = relationship("Educator", back_populates="student_relationships")
    student = relationship("Student", back_populates="educator_relationships")
