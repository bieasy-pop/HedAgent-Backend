import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.educator import Educator
from app.models.educator_approval import EducatorApproval, ApprovalStatus
from app.middleware.auth_middleware import require_role
from app.services.onesignal_service import send_push

router = APIRouter()


class ApprovalAction(BaseModel):
    educator_user_id: str
    action: str                         # "approve" or "reject"
    rejection_reason: Optional[str] = None


@router.get("/pending-educators", summary="List educators pending approval")
def pending_educators(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Super admins see all educators waiting for approval."""
    pending = db.query(EducatorApproval).filter(
        EducatorApproval.status == ApprovalStatus.pending
    ).all()

    results = []
    for p in pending:
        user = db.query(User).filter(User.id == p.educator_user_id).first()
        educator = db.query(Educator).filter(Educator.user_id == p.educator_user_id).first()
        if user:
            results.append({
                "approval_id": p.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "university_name": user.university_name,
                "department": educator.department if educator else None,
                "designation": educator.designation if educator else None,
                "staff_id": educator.staff_id if educator else None,
                "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
            })

    return {"success": True, "count": len(results), "pending": results}


@router.post("/approve-educator", summary="Approve or reject an educator")
async def approve_educator(
    payload: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """
    Super admin approves or rejects an educator.
    On approval: educator.is_approved = True, user remains active.
    On rejection: user.is_active = False, reason stored.
    Push notification sent to the educator.
    """
    approval = db.query(EducatorApproval).filter(
        EducatorApproval.educator_user_id == payload.educator_user_id
    ).first()

    if not approval:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Approval record not found.", "code": "NOT_FOUND"})
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=409, detail={"success": False, "message": f"This educator has already been {approval.status.value}.", "code": "ALREADY_REVIEWED"})

    if payload.action not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail={"success": False, "message": "Action must be 'approve' or 'reject'.", "code": "INVALID_ACTION"})

    educator = db.query(Educator).filter(Educator.user_id == payload.educator_user_id).first()
    user = db.query(User).filter(User.id == payload.educator_user_id).first()

    approval.reviewed_by = current_user["uid"]
    approval.reviewed_at = datetime.now(timezone.utc)

    if payload.action == "approve":
        approval.status = ApprovalStatus.approved
        if educator:
            educator.is_approved = True
        message = "Your educator account has been approved. You can now log in and access the system."
        title = "Account approved ✅"
    else:
        if not payload.rejection_reason:
            raise HTTPException(status_code=422, detail={"success": False, "message": "Rejection reason is required.", "code": "REASON_REQUIRED"})
        approval.status = ApprovalStatus.rejected
        approval.rejection_reason = payload.rejection_reason
        if user:
            user.is_active = False
        message = f"Your educator account application was not approved. Reason: {payload.rejection_reason}"
        title = "Account application update"

    db.commit()

    # Notify the educator
    if user and user.onesignal_player_id:
        await send_push(
            player_ids=[user.onesignal_player_id],
            title=title,
            message=message,
            data={"type": "approval_update", "status": payload.action}
        )

    return {
        "success": True,
        "message": f"Educator {payload.action}d successfully.",
        "educator_id": payload.educator_user_id,
        "status": payload.action,
    }


@router.get("/all-users", summary="List all users")
def all_users(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.all()
    return {
        "success": True,
        "count": len(users),
        "users": [{
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role.value if u.role else None,
            "university_name": u.university_name,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        } for u in users],
    }
