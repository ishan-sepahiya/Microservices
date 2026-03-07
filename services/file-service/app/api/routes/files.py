import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.file import FileRecord, FileStatus
from app.schemas.file import FileResponse
from app.services.storage import upload_file, generate_presigned_url, delete_file

from jose import jwt, JWTError

router = APIRouter(prefix="/api/files", tags=["Files"])
security = HTTPBearer()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf", "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "video/mp4", "audio/mpeg",
}


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload(
    file: UploadFile = File(...),
    description: str | None = None,
    is_public: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"File type '{file.content_type}' not allowed")

    # Read file and check size
    data = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    # Generate unique stored filename
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
    stored_filename = f"{user_id}/{uuid.uuid4()}.{ext}" if ext else f"{user_id}/{uuid.uuid4()}"

    # Create DB record first
    file_record = FileRecord(
        user_id=user_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        size_bytes=len(data),
        bucket=settings.MINIO_BUCKET,
        is_public=is_public,
        description=description,
        status=FileStatus.UPLOADING,
    )
    db.add(file_record)
    await db.flush()

    # Upload to MinIO
    success = upload_file(stored_filename, data, file.content_type)
    file_record.status = FileStatus.READY if success else FileStatus.FAILED
    file_record.updated_at = datetime.now(timezone.utc)
    await db.commit()

    if not success:
        raise HTTPException(status_code=500, detail="File upload failed")

    return file_record


@router.get("/", response_model=list[FileResponse])
async def list_files(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.user_id == user_id, FileRecord.status != FileStatus.DELETED)
        .order_by(desc(FileRecord.created_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{file_id}/download-url")
async def get_download_url(
    file_id: uuid.UUID,
    expires_hours: int = Query(default=1, le=24),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FileRecord).where(
            FileRecord.id == file_id,
            FileRecord.status == FileStatus.READY,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Only owner can access private files
    if not file_record.is_public and file_record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    url = generate_presigned_url(file_record.stored_filename, expires_hours)
    if not url:
        raise HTTPException(status_code=500, detail="Could not generate download URL")

    return {"download_url": url, "expires_in_hours": expires_hours}


@router.delete("/{file_id}", status_code=204)
async def delete_file_endpoint(
    file_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FileRecord).where(FileRecord.id == file_id, FileRecord.user_id == user_id)
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    delete_file(file_record.stored_filename)
    file_record.status = FileStatus.DELETED
    await db.commit()
