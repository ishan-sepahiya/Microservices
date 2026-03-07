import io
from minio import Minio
from minio.error import S3Error
from loguru import logger

from app.core.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # Ensure bucket exists
        try:
            if not _client.bucket_exists(settings.MINIO_BUCKET):
                _client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Created bucket: {settings.MINIO_BUCKET}")
        except S3Error as e:
            logger.error(f"MinIO bucket setup failed: {e}")
    return _client


def upload_file(stored_filename: str, data: bytes, content_type: str) -> bool:
    """Upload file bytes to MinIO"""
    try:
        client = get_minio_client()
        client.put_object(
            settings.MINIO_BUCKET,
            stored_filename,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info(f"Uploaded file: {stored_filename} ({len(data)} bytes)")
        return True
    except S3Error as e:
        logger.error(f"Failed to upload {stored_filename}: {e}")
        return False


def generate_presigned_url(stored_filename: str, expires_hours: int = 1) -> str | None:
    """Generate a time-limited download URL"""
    try:
        from datetime import timedelta
        client = get_minio_client()
        url = client.presigned_get_object(
            settings.MINIO_BUCKET,
            stored_filename,
            expires=timedelta(hours=expires_hours),
        )
        return url
    except S3Error as e:
        logger.error(f"Failed to generate presigned URL for {stored_filename}: {e}")
        return None


def delete_file(stored_filename: str) -> bool:
    """Delete a file from MinIO"""
    try:
        client = get_minio_client()
        client.remove_object(settings.MINIO_BUCKET, stored_filename)
        logger.info(f"Deleted file: {stored_filename}")
        return True
    except S3Error as e:
        logger.error(f"Failed to delete {stored_filename}: {e}")
        return False
