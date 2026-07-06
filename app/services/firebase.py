import json
import firebase_admin
from firebase_admin import credentials, auth
from app.config import settings


def _get_app():
    """
    Lazily initializes Firebase Admin SDK.
    Returns the initialized app or raises a clear error if credentials are missing.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    raw = settings.FIREBASE_CREDENTIALS_JSON.strip()

    if not raw or raw == "{}":
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_JSON is empty. "
            "Paste your serviceAccountKey.json content as a single-line JSON string in .env"
        )

    try:
        cred_dict = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"FIREBASE_CREDENTIALS_JSON is not valid JSON: {e}")

    required_keys = ["type", "project_id", "private_key", "client_email"]
    missing = [k for k in required_keys if k not in cred_dict]
    if missing:
        raise RuntimeError(
            f"FIREBASE_CREDENTIALS_JSON is missing required keys: {missing}"
        )

    cred = credentials.Certificate(cred_dict)
    return firebase_admin.initialize_app(cred)


def verify_firebase_token(token: str) -> dict:
    """
    Verifies a Firebase ID token.
    Returns decoded payload with uid, email, role, email_verified.
    """
    _get_app()
    decoded = auth.verify_id_token(token)
    return {
        "uid": decoded["uid"],
        "email": decoded.get("email", ""),
        "role": decoded.get("role", "student"),
        "email_verified": decoded.get("email_verified", False),
    }


def set_user_role_claim(uid: str, role: str) -> None:
    """Sets a custom 'role' claim on a Firebase user."""
    _get_app()
    auth.set_custom_user_claims(uid, {"role": role})
