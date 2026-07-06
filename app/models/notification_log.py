from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(String, primary_key=True)
    recipient_id = Column(String, nullable=False, index=True)     # User.id
    onesignal_notification_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON, default={})
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
