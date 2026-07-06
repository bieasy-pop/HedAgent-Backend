from fastapi import Depends, HTTPException, Header, status
from app.services.firebase import verify_firebase_token


async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    FastAPI dependency. Extracts and verifies the Firebase Bearer token.
    Returns decoded token data: { uid, email, role, raw_token }
    raw_token is included so endpoints that need to call Firebase REST API
    on behalf of the user (e.g. send verification email) can use it directly.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Invalid authorization header. Format: Bearer <token>",
                "code": "INVALID_AUTH_HEADER",
            }
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        decoded = verify_firebase_token(token)
        decoded["raw_token"] = token   # pass through for REST API calls
        return decoded
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Token is invalid or has expired. Please log in again.",
                "code": "INVALID_TOKEN",
            }
        )


def require_role(*roles: str):
    """
    Role-guard factory. Usage:
        @router.get("/", dependencies=[Depends(require_role("educator", "admin"))])
    """
    async def _check(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": f"Access restricted to: {', '.join(roles)}",
                    "code": "ACCESS_DENIED",
                }
            )
        return current_user
    return _check
