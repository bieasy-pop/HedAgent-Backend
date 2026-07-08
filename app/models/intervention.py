from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class InterventionStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    escalated = "escalated"


class InterventionType(str, enum.Enum):
    academic = "academic"
    attendance = "attendance"
    behavioural = "behavioural"
    wellbeing = "wellbeing"
    potential = "potential"      # high-potential enrichment


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    raised_by = Column(String, ForeignKey("users.id"), nullable=False)     # educator/admin UID, or the student themself for goal-driven interventions
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=True, index=True)   # set when AI-generated from a student goal

    type = Column(Enum(InterventionType), nullable=False)
    status = Column(Enum(InterventionStatus), default=InterventionStatus.open)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    ai_recommendation = Column(Text, nullable=True)   # OpenAI-generated action plan
    attachment_url = Column(String, nullable=True)    # Cloudinary URL

    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student = relationship("Student", back_populates="interventions")
    raiser = relationship("User", foreign_keys=[raised_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    goal = relationship("Goal", back_populates="interventions")
