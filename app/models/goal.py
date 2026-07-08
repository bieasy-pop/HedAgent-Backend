from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)

    description = Column(Text, nullable=False)
    ai_summary = Column(Text, nullable=True)   # AI framing of the goal + why these interventions were chosen

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="goals")
    interventions = relationship("Intervention", back_populates="goal", lazy="dynamic")
