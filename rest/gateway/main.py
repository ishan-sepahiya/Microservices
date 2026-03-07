"""
main.py — REST Gateway (port 8000)
Routes all REST API traffic to product-service and payment-service.
Add new services by extending ROUTES below.
"""
import os, logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002")

ROUTES: list[tuple[str, str]] = [
    ("/api/products", PRODUCT_SERVICE_URL),
    ("/api/payments", PAYMENT_SERVICE_URL),
]

logger = logging.getLogger("rest-gateway")
_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _client
    _client = httpx.AsyncClient(timeout=30.0)
    yield
    await _client.aclose()

app = FastAPI(title="REST Gateway", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def _resolve(path: str) -> str | None:
    for prefix, upstream in ROUTES:
        if path.startswith(prefix):
            return upstream
    return None

def _strip(path: str) -> str:
    return path[4:] if path.startswith("/api") else path  # /api/products -> /products

@app.api_route("/{full_path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def proxy(request: Request, full_path: str) -> Response:
    path = "/" + full_path
    upstream = _resolve(path)
    if not upstream:
        raise HTTPException(status_code=404, detail=f"No route for {path}")
    url = upstream.rstrip("/") + _strip(path)
    if request.url.query:
        url += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    try:
        r = await _client.request(request.method, url, headers=headers, content=await request.body())
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Upstream unavailable: {upstream}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timed out")
    skip = {"transfer-encoding", "connection", "keep-alive"}
    resp_headers = {k: v for k, v in r.headers.items() if k.lower() not in skip}
    return Response(content=r.content, status_code=r.status_code, headers=resp_headers,
                    media_type=r.headers.get("content-type"))

@app.get("/health")
async def health():
    checks = {"gateway": "ok"}
    for name, url in [("product-service", PRODUCT_SERVICE_URL), ("payment-service", PAYMENT_SERVICE_URL)]:
        try:
            r = await _client.get(f"{url}/health", timeout=3.0)
            checks[name] = "ok" if r.status_code == 200 else f"degraded ({r.status_code})"
        except Exception as e:
            checks[name] = f"unreachable"
    return JSONResponse({"status": "ok" if all(v == "ok" for v in checks.values()) else "degraded", "services": checks})
