import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.notification_log import NotificationLog
from app.middleware.auth_middleware import require_role
from app.services.onesignal_service import send_push, send_push_to_segments

router = APIRouter()


class PushRequest(BaseModel):
    recipient_ids: list[str]   # User IDs (not OneSignal player IDs)
    title: str
    message: str
    data: dict = {}


class BroadcastRequest(BaseModel):
    segments: list[str]        # OneSignal segment names
    title: str
    message: str
    data: dict = {}


@router.post("/send")
async def send_notification(
    payload: PushRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("educator", "admin")),
):
    """Send a push notification to specific users by their User IDs."""
    users = db.query(User).filter(User.id.in_(payload.recipient_ids)).all()
    player_ids = [u.onesignal_player_id for u in users if u.onesignal_player_id]

    if not player_ids:
        raise HTTPException(status_code=400, detail="No valid device tokens found for recipients")

    result = await send_push(player_ids, payload.title, payload.message, payload.data)

    # Log the notification
    for user in users:
        db.add(NotificationLog(
            id=str(uuid.uuid4()),
            recipient_id=user.id,
            onesignal_notification_id=result.get("id"),
            title=payload.title,
            message=payload.message,
            data=payload.data,
            delivered=True,
        ))
    db.commit()

    return {"sent_to": len(player_ids), "onesignal_response": result}


@router.post("/broadcast")
async def broadcast_notification(
    payload: BroadcastRequest,
    current_user: dict = Depends(require_role("admin")),
):
    """Broadcast to a OneSignal segment. Admin only."""
    result = await send_push_to_segments(
        payload.segments, payload.title, payload.message, payload.data
    )
    return {"onesignal_response": result}
