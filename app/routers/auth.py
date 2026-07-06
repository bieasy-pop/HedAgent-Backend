import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.educator import Educator
from app.schemas.auth import (
    RegisterRequest, LoginRequest,
    RegisterResponse, LoginResponse,
    EmailVerificationResponse, UserResponse,
    ErrorResponse,
)
from app.services.firebase import set_user_role_claim
from app.middleware.auth_middleware import get_current_user
from app.config import settings

router = APIRouter()


# ── Firebase URLs ─────────────────────────────────────────────────────────────

FIREBASE_SIGNUP_URL  = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={settings.FIREBASE_WEB_API_KEY}"
FIREBASE_SIGNIN_URL  = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_WEB_API_KEY}"
FIREBASE_LOOKUP_URL  = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={settings.FIREBASE_WEB_API_KEY}"
FIREBASE_VERIFY_EMAIL_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={settings.FIREBASE_WEB_API_KEY}"


# ── Firebase REST helpers ─────────────────────────────────────────────────────

def _firebase_signup(email: str, password: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        res = client.post(FIREBASE_SIGNUP_URL, json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        })
    data = res.json()
    if "error" in data:
        code = data["error"].get("message", "UNKNOWN_ERROR")
        if code == "EMAIL_EXISTS":
            raise HTTPException(status_code=409, detail={"success": False, "message": "This email is already registered.", "code": "EMAIL_EXISTS"})
        if code == "INVALID_EMAIL":
            raise HTTPException(status_code=422, detail={"success": False, "message": "The email address is not valid.", "code": "INVALID_EMAIL"})
        if "WEAK_PASSWORD" in code:
            raise HTTPException(status_code=422, detail={"success": False, "message": "Password must be at least 6 characters.", "code": "WEAK_PASSWORD"})
        raise HTTPException(status_code=400, detail={"success": False, "message": f"Registration failed: {code}", "code": code})
    return {
        "uid": data["localId"],
        "email": data["email"],
        "id_token": data["idToken"],
        "refresh_token": data["refreshToken"],
    }


def _firebase_signin(email: str, password: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        res = client.post(FIREBASE_SIGNIN_URL, json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        })
    data = res.json()
    if "error" in data:
        code = data["error"].get("message", "UNKNOWN_ERROR")
        if code in ("EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"):
            raise HTTPException(status_code=401, detail={"success": False, "message": "Invalid email or password.", "code": "INVALID_CREDENTIALS"})
        if code == "USER_DISABLED":
            raise HTTPException(status_code=403, detail={"success": False, "message": "This account has been disabled.", "code": "USER_DISABLED"})
        if code == "TOO_MANY_ATTEMPTS_TRY_LATER":
            raise HTTPException(status_code=429, detail={"success": False, "message": "Too many failed attempts. Please try again later.", "code": "TOO_MANY_ATTEMPTS"})
        raise HTTPException(status_code=400, detail={"success": False, "message": f"Login failed: {code}", "code": code})

    # Fetch email_verified from lookup
    with httpx.Client(timeout=10.0) as client:
        lookup = client.post(FIREBASE_LOOKUP_URL, json={"idToken": data["idToken"]})
    user_info = lookup.json().get("users", [{}])[0]

    return {
        "uid": data["localId"],
        "email": data["email"],
        "id_token": data["idToken"],
        "refresh_token": data["refreshToken"],
        "email_verified": user_info.get("emailVerified", False),
    }


def _firebase_check_verified(id_token: str) -> dict:
    """Looks up the current email_verified status directly from Firebase."""
    with httpx.Client(timeout=10.0) as client:
        res = client.post(FIREBASE_LOOKUP_URL, json={"idToken": id_token})
    data = res.json()
    if "error" in data:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "message": "Invalid or expired token.", "code": "INVALID_TOKEN"}
        )
    user_info = data.get("users", [{}])[0]
    return {
        "uid": user_info.get("localId"),
        "email": user_info.get("email"),
        "email_verified": user_info.get("emailVerified", False),
    }


# ── DB helpers ────────────────────────────────────────────────────────────────

def _load_user(db: Session, uid: str) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.student_profile), joinedload(User.educator_profile))
        .filter(User.id == uid)
        .first()
    )


def _build_user_data(user: User) -> dict:
    """Serialise User ORM object to a plain dict safe for JSON responses."""
    def ev(v):   # enum → string
        return v.value if hasattr(v, "value") else v
    def dv(v):   # date → ISO string
        return v.isoformat() if v else None

    sp = getattr(user, "student_profile", None)
    ep = getattr(user, "educator_profile", None)

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "other_name": user.other_name,
        "full_name": user.full_name,
        "university_name": user.university_name,
        "phone_number": user.phone_number,
        "gender": ev(user.gender),
        "date_of_birth": dv(user.date_of_birth),
        "role": ev(user.role),
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "student_profile": {
            "student_number": sp.student_number,
            "faculty": sp.faculty,
            "department": sp.department,
            "programme": sp.programme,
            "level": sp.level,
            "year_of_admission": sp.year_of_admission,
            "expected_graduation": sp.expected_graduation,
            "gpa": sp.gpa,
            "attendance_rate": sp.attendance_rate,
            "risk_label": sp.risk_label,
        } if sp else None,
        "educator_profile": {
            "staff_id": ep.staff_id,
            "faculty": ep.faculty,
            "department": ep.department,
            "designation": ep.designation,
            "specialization": ep.specialization,
        } if ep else None,
    }


# ── Debug (remove before production) ─────────────────────────────────────────

@router.get(
    "/debug",
    summary="Check environment config",
    tags=["Debug"],
)
def debug_config():
    import json
    raw = settings.FIREBASE_CREDENTIALS_JSON.strip()
    web_key = settings.FIREBASE_WEB_API_KEY
    try:
        parsed = json.loads(raw)
        cred_status = "valid"
        project_id = parsed.get("project_id")
    except Exception as e:
        cred_status = f"invalid JSON: {e}"
        project_id = None
    return {
        "FIREBASE_CREDENTIALS_JSON": cred_status,
        "project_id": project_id,
        "FIREBASE_WEB_API_KEY": f"{web_key[:8]}..." if len(web_key) > 8 else "missing",
        "OPENAI_API_KEY": "set" if settings.OPENAI_API_KEY else "missing",
        "DATABASE_URL": "set" if settings.DATABASE_URL else "missing",
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error (weak password, invalid email)"},
        500: {"model": ErrorResponse, "description": "Database error"},
    },
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
Creates a Firebase account and saves the user profile to the database in one call.
Returns a Firebase **ID token** to use as a Bearer token on all subsequent requests.

**Flutter usage:**
Store the `token` from the response and attach it to every API request:
`Authorization: Bearer <token>`
""",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # 1. Create Firebase account
    firebase_user = _firebase_signup(payload.email, payload.password)
    uid = firebase_user["uid"]

    # 2. Return existing user (idempotent safety)
    existing = _load_user(db, uid)
    if existing:
        return {
            "success": True,
            "message": "Account already exists. Returning existing profile.",
            "token": firebase_user["id_token"],
            "user": _build_user_data(existing),
        }

    # 3. Save base user
    user = User(
        id=uid,
        email=firebase_user["email"],
        first_name=payload.first_name,
        last_name=payload.last_name,
        other_name=payload.other_name,
        university_name=payload.university_name,
        phone_number=payload.phone_number,
        gender=payload.gender,
        date_of_birth=payload.date_of_birth,
        role=payload.role,
        onesignal_player_id=payload.onesignal_player_id,
        is_verified=False,
    )
    db.add(user)

    # 4. Save role-specific profile
    if payload.role == UserRole.student:
        fields = payload.student_data.model_dump() if payload.student_data else {}
        db.add(Student(id=str(uuid.uuid4()), user_id=uid, **fields))
    elif payload.role == UserRole.educator:
        fields = payload.educator_data.model_dump() if payload.educator_data else {}
        db.add(Educator(id=str(uuid.uuid4()), user_id=uid, **fields))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        try:
            from firebase_admin import auth as fa
            fa.delete_user(uid)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": f"Failed to save user: {str(e)}", "code": "DB_ERROR"}
        )

    try:
        set_user_role_claim(uid, payload.role.value)
    except Exception:
        pass

    user = _load_user(db, uid)
    return {
        "success": True,
        "message": "Account created successfully. Please verify your email.",
        "token": firebase_user["id_token"],
        "user": _build_user_data(user),
    }


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        403: {"model": ErrorResponse, "description": "Account disabled"},
        404: {"model": ErrorResponse, "description": "User not registered"},
        429: {"model": ErrorResponse, "description": "Too many attempts"},
    },
    summary="Sign in a user",
    description="""
Authenticates the user with Firebase and returns their profile plus tokens.

- **token** — Firebase ID token. Short-lived (~1 hour). Attach as `Authorization: Bearer <token>` on every API call.
- **refresh_token** — Long-lived. Use this to get a new ID token when the current one expires.
""",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    firebase_user = _firebase_signin(payload.email, payload.password)

    user = _load_user(db, firebase_user["uid"])
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": "No account found for this email. Please register first.", "code": "USER_NOT_FOUND"}
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "Your account has been deactivated.", "code": "ACCOUNT_INACTIVE"}
        )

    # Refresh email verification status + device token
    user.is_verified = firebase_user.get("email_verified", user.is_verified)
    if payload.onesignal_player_id:
        user.onesignal_player_id = payload.onesignal_player_id
    db.commit()

    user = _load_user(db, user.id)
    return {
        "success": True,
        "message": "Login successful.",
        "token": firebase_user["id_token"],
        "refresh_token": firebase_user["refresh_token"],
        "user": _build_user_data(user),
    }


@router.get(
    "/verify-email",
    response_model=EmailVerificationResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
    summary="Check email verification status",
    description="""
Checks whether the authenticated user has verified their email address.

Pass the Firebase ID token as `Authorization: Bearer <token>`.

**Two possible outcomes:**
- `is_verified: true` — email is confirmed, full access granted.
- `is_verified: false` — email not yet confirmed, prompt user to check inbox.

The DB record is also updated to reflect the current status.
""",
)
def check_email_verified(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Re-query Firebase for the real-time email_verified status
    # (the JWT claim only refreshes when the token is re-issued)
    from app.services.firebase import verify_firebase_token
    from fastapi import Header
    import inspect

    # Get the raw token from the current user's uid via Firebase Admin
    from firebase_admin import auth as fa
    firebase_record = fa.get_user(current_user["uid"])
    is_verified = firebase_record.email_verified

    # Sync to DB
    user = db.query(User).filter(User.id == current_user["uid"]).first()
    if user:
        user.is_verified = is_verified
        db.commit()

    if is_verified:
        return {
            "success": True,
            "message": "Your email has been verified successfully.",
            "is_verified": True,
            "email": firebase_record.email,
        }
    else:
        return {
            "success": False,
            "message": "Email not yet verified. Please check your inbox and click the verification link.",
            "is_verified": False,
            "email": firebase_record.email,
        }


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
    summary="Get current user profile",
    description="""
Returns the full profile of the currently authenticated user.

Requires `Authorization: Bearer <token>` header.

The response includes:
- Personal details (name, email, university, gender, DOB)
- Role (student / educator / admin)
- Role-specific profile (academic data for students, staff info for educators)
- Email verification status
""",
)
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _load_user(db, current_user["uid"])
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": "User not found.", "code": "USER_NOT_FOUND"}
        )
    return {
        "success": True,
        "message": "User retrieved successfully.",
        "user": _build_user_data(user),
    }
