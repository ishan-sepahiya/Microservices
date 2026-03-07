import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import notifications
from app.core.config import settings
from app.db.database import engine, Base
from app.services.consumer import start_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start RabbitMQ consumer in background
    consumer_task = asyncio.create_task(start_consumer())

    yield

    consumer_task.cancel()
    logger.info(f"Shutting down {settings.APP_NAME}")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Handles email and SMS notifications triggered by events from other services",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notifications.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": settings.APP_NAME}
