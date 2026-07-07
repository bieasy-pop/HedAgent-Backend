from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EducatorApproval(Base):
    """
    Super admins must approve new educators before they can access the system.
    Created automatically when a user registers with role=educator.
    """
    __tablename__ = "educator_approvals"

    id = Column(String, primary_key=True)
    educator_user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)   # super admin UID

    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    rejection_reason = Column(Text, nullable=True)

    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    applicant = relationship("User", foreign_keys=[educator_user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
