from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ReminderType(str, enum.Enum):
    assignment = "assignment"
    attendance = "attendance"
    exam = "exam"
    consultation = "consultation"
    general = "general"
    intervention = "intervention"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)   # educator/admin UID

    type = Column(Enum(ReminderType), nullable=False, default=ReminderType.general)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)

    is_sent = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="reminders")
