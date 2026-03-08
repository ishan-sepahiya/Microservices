from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import files
from app.core.config import settings
from app.db.database import engine, Base
from app.services.storage import get_minio_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize MinIO connection and bucket
    get_minio_client()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Handles file uploads, storage (MinIO/S3), and presigned download URLs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": settings.APP_NAME}
