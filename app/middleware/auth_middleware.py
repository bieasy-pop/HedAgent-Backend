from fastapi import Depends, HTTPException, Header, status
from app.services.firebase import verify_firebase_token


async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    FastAPI dependency. Extracts and verifies the Firebase Bearer token.
    Returns decoded token data: { uid, email, role }
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_firebase_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
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
                detail=f"Access restricted to roles: {', '.join(roles)}",
            )
        return current_user
    return _check
