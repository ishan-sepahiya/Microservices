"""
main.py — Agent Service (port 8020)
Starts: Control API + background health monitor
Tables are created by `alembic upgrade head` in the Docker CMD.
create_all() here is a safety net only.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine, Base
from control_api.routes import router as control_router
from registry.health_monitor import run_health_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s %(asctime)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Safety net: create tables if alembic somehow didn't run
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Agent service ready — starting health monitor")
    monitor = asyncio.create_task(run_health_monitor())
    yield
    monitor.cancel()
    try:
        await monitor
    except asyncio.CancelledError:
        pass
    await engine.dispose()


app = FastAPI(
    title="Agent Control API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control_router)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "service": "agent", "version": "2.0.0"}
