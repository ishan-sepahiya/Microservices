import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.notification import NotificationType, NotificationStatus


class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: str
    type: NotificationType
    status: NotificationStatus
    recipient: str
    subject: str | None
    template: str
    created_at: datetime
    sent_at: datetime | None


class SendNotificationRequest(BaseModel):
    user_id: str
    type: NotificationType
    recipient: str
    template: str
    context: dict = {}
