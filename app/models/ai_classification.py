from sqlalchemy import Column, String, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AIClassification(Base):
    """
    Stores each AI classification run for a student.
    Keeps history so educators can track changes over time.
    """
    __tablename__ = "ai_classifications"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)

    # Classification
    risk_label = Column(String, nullable=False)        # at_risk / high_potential / average / on_track / critical
    risk_score = Column(Float, nullable=False)          # 0.0 - 1.0
    gpa_at_time = Column(Float, nullable=True)
    attendance_at_time = Column(Float, nullable=True)

    # AI-generated content
    summary = Column(Text, nullable=False)             # brief situation summary
    remarks = Column(Text, nullable=False)             # actionable remarks for student
    educator_alert = Column(Text, nullable=True)       # alert message for the linked educator
    recommendations = Column(JSON, default=[])         # list of action items

    # Meta
    model_used = Column(String, default="gemini-1.5-flash")
    triggered_by = Column(String, nullable=True)       # "system" / "educator" / "manual"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="ai_classifications")
