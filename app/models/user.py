from sqlalchemy import Column, String, Boolean, DateTime, Enum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    educator = "educator"
    admin = "admin"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    other_name = Column(String, nullable=True)

    university_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    role = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    onesignal_player_id = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    # Relationships — use back_populates, not backref, to avoid conflicts
    student_profile = relationship("Student", back_populates="user", uselist=False)
    educator_profile = relationship("Educator", back_populates="user", uselist=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def full_name(self) -> str:
        parts = [self.first_name]
        if self.other_name:
            parts.append(self.other_name)
        parts.append(self.last_name)
        return " ".join(parts)
