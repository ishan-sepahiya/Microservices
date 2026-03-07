import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.file import FileStatus


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    status: FileStatus
    is_public: bool
    description: str | None
    created_at: datetime
