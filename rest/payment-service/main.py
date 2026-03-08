"""main.py — Payment Service (port 8002)"""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine
from routes import router
from startup import register_with_agent
from otel_middleware import setup_otel

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await register_with_agent()
    yield
    await engine.dispose()

app = FastAPI(title="Payment Service", version="1.0.0", lifespan=lifespan,
              docs_url="/docs" if settings.debug else None)
setup_otel(app, service_name="payment-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "payment-service"}
