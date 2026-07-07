from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date
from app.models.user import UserRole, Gender


# ── Shared error shape — used across all endpoints ────────────────────────────

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: Optional[str] = None     # machine-readable error code e.g. "EMAIL_EXISTS"


# ── Role-specific nested data ─────────────────────────────────────────────────

class StudentRegisterData(BaseModel):
    student_number: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    programme: Optional[str] = None
    level: Optional[str] = None
    year_of_admission: Optional[str] = None
    expected_graduation: Optional[str] = None


class EducatorRegisterData(BaseModel):
    staff_id: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    specialization: Optional[str] = None


# ── Requests ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    other_name: Optional[str] = None
    university_name: str
    role: UserRole = UserRole.student
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    student_data: Optional[StudentRegisterData] = None
    educator_data: Optional[EducatorRegisterData] = None
    onesignal_player_id: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name fields cannot be blank")
        return v.strip().title()

    @field_validator("other_name", mode="before")
    @classmethod
    def clean_other_name(cls, v):
        return v.strip().title() if v else v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    onesignal_player_id: Optional[str] = None


class UserAdminUpdate(BaseModel):
    """Fields an admin may edit on any user. `id`, `email`, and `role` are
    excluded — email/id are tied to the Firebase auth record, and role
    changes require creating/removing the linked Student/Educator profile
    row, which is handled elsewhere."""
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    other_name: Optional[str] = None
    university_name: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def name_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Name fields cannot be blank")
        return v.strip().title() if v else v

    @field_validator("other_name", mode="before")
    @classmethod
    def clean_other_name(cls, v):
        return v.strip().title() if v else v


# ── Profile sub-responses ─────────────────────────────────────────────────────

class StudentProfileResponse(BaseModel):
    student_number: Optional[str]
    faculty: Optional[str]
    department: Optional[str]
    programme: Optional[str]
    level: Optional[str]
    year_of_admission: Optional[str]
    expected_graduation: Optional[str]
    gpa: Optional[float]
    attendance_rate: Optional[float]
    risk_label: str


class EducatorProfileResponse(BaseModel):
    staff_id: Optional[str]
    faculty: Optional[str]
    department: Optional[str]
    designation: Optional[str]
    specialization: Optional[str]


class UserData(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    other_name: Optional[str]
    full_name: str
    university_name: str
    phone_number: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[str]
    role: str
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    student_profile: Optional[StudentProfileResponse] = None
    educator_profile: Optional[EducatorProfileResponse] = None


# ── Standardised success responses ───────────────────────────────────────────

class RegisterResponse(BaseModel):
    success: bool = True
    message: str
    token: str                  # Firebase ID token — Flutter stores this for auth headers
    user: UserData


class LoginResponse(BaseModel):
    success: bool = True
    message: str
    token: str                  # Firebase ID token
    refresh_token: str          # Firebase refresh token — for token renewal
    user: UserData


class EmailVerificationResponse(BaseModel):
    success: bool
    message: str
    is_verified: bool
    email: str


class UserResponse(BaseModel):
    success: bool = True
    message: str = "User retrieved successfully"
    user: UserData
