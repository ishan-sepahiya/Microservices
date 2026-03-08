"""main.py — Chat Service (port 8011)"""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import httpx, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine
from routes import router
from otel_middleware import setup_otel

logger = logging.getLogger("chat")


async def register_with_agent():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.agent_service_url}/control/register",
                headers={"X-Control-Key": settings.agent_api_key},
                json={
                    "name": "chat-service",
                    "service_type": "websocket",
                    "base_url": "http://chat-service:8011",
                    "health_url": "http://chat-service:8011/health",
                    "description": "Real-time WebSocket chat with message history",
                    "instructions": "Monitor active WebSocket connections. Alert if connections drop to 0 unexpectedly. Alert on any errors.",
                },
            )
    except Exception as e:
        logger.warning("Could not register with agent: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await register_with_agent()
    yield
    await engine.dispose()


app = FastAPI(title="Chat Service", version="1.0.0", lifespan=lifespan,
              docs_url="/docs" if settings.debug else None)
setup_otel(app, service_name="chat-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
async def health():
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "chat-service",
        "checks": {"database": "ok" if db_ok else "error"},
    }
