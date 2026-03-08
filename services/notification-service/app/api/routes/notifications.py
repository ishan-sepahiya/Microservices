from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.notification import NotificationLog
from app.schemas.notification import NotificationLogResponse, SendNotificationRequest
from app.services.sender import send_email, send_sms
from app.services.templates import render_template

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/send")
async def send_notification(body: SendNotificationRequest, db: AsyncSession = Depends(get_db)):
    """Manually trigger a notification (for testing or admin use)"""
    if body.type == "email":
        subject, html_body = render_template(body.template, body.context)
        success = await send_email(body.recipient, subject, html_body)
    else:
        message = body.context.get("message", "")
        success = await send_sms(body.recipient, message)

    return {"success": success, "recipient": body.recipient}


@router.get("/logs/{user_id}", response_model=list[NotificationLogResponse])
async def get_user_notification_logs(
    user_id: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get notification history for a user"""
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == user_id)
        .order_by(desc(NotificationLog.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "Notification Service"}
