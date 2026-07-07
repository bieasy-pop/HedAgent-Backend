from sqlalchemy import Column, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    student_number = Column(String, unique=True, nullable=True)
    faculty = Column(String, nullable=True)
    department = Column(String, nullable=True)
    programme = Column(String, nullable=True)
    level = Column(String, nullable=True)
    year_of_admission = Column(String, nullable=True)
    expected_graduation = Column(String, nullable=True)

    gpa = Column(Float, nullable=True)
    attendance_rate = Column(Float, nullable=True)

    risk_score = Column(Float, default=0.0)
    risk_label = Column(String, default="unclassified")   # at_risk/high_potential/average/on_track/critical
    ai_summary = Column(String, nullable=True)

    meta = Column(JSON, default={})

    user = relationship("User", back_populates="student_profile")
    interventions = relationship("Intervention", back_populates="student", lazy="dynamic")
    courses = relationship("StudentCourse", back_populates="student", lazy="dynamic")
    educator_relationships = relationship("EducatorStudent", back_populates="student", lazy="dynamic")
    ai_classifications = relationship("AIClassification", back_populates="student", lazy="dynamic")
    reminders = relationship("Reminder", back_populates="student", lazy="dynamic")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
