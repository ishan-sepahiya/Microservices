"""
main.py — Agent Service (port 8020)
Control API + health monitor + LangGraph AI agent + Streamlit dashboard
"""
import asyncio, logging, sys, os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine
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
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(control_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "agent"}
