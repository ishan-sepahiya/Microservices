"""
main.py — WebSocket Gateway (port 9000)
Proxies WebSocket connections AND REST calls to WS services.
ws://host:9000/ws/chat/{room_id} -> chat-service:8011
ws://host:9000/ws/metrics        -> metrics-service:8012
REST /api/rooms, /api/metrics/history -> same services
"""
import os, logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import httpx
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketState

CHAT_SERVICE_URL    = os.getenv("CHAT_SERVICE_URL",    "http://chat-service:8011")
METRICS_SERVICE_URL = os.getenv("METRICS_SERVICE_URL", "http://metrics-service:8012")

REST_ROUTES = [
    ("/api/rooms",           CHAT_SERVICE_URL),
    ("/api/metrics",         METRICS_SERVICE_URL),
]

logger = logging.getLogger("ws-gateway")
_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _client
    _client = httpx.AsyncClient(timeout=30.0)
    yield
    await _client.aclose()

app = FastAPI(title="WebSocket Gateway", version="1.0.0", lifespan=lifespan, docs_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── WebSocket proxying ────────────────────────────────────────────────────────
@app.websocket("/ws/chat/{room_id}")
async def proxy_chat(room_id: str, ws: WebSocket, sender_id: str = "anonymous"):
    upstream_url = f"ws://chat-service:8011/ws/chat/{room_id}?sender_id={sender_id}"
    await _proxy_websocket(ws, upstream_url)

@app.websocket("/ws/metrics")
async def proxy_metrics(ws: WebSocket, services: str = "all", interval: float = 2.0):
    upstream_url = f"ws://metrics-service:8012/ws/metrics?services={services}&interval={interval}"
    await _proxy_websocket(ws, upstream_url)

async def _proxy_websocket(client_ws: WebSocket, upstream_url: str):
    """Bidirectional WebSocket proxy."""
    import websockets
    await client_ws.accept()
    try:
        async with websockets.connect(upstream_url) as upstream_ws:
            async def forward_to_upstream():
                while True:
                    try:
                        data = await client_ws.receive_text()
                        await upstream_ws.send(data)
                    except WebSocketDisconnect:
                        break

            async def forward_to_client():
                async for message in upstream_ws:
                    if client_ws.client_state == WebSocketState.CONNECTED:
                        await client_ws.send_text(message)
                    else:
                        break

            import asyncio
            done, pending = await asyncio.wait(
                [asyncio.create_task(forward_to_upstream()),
                 asyncio.create_task(forward_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
    except Exception as e:
        logger.error("WS proxy error: %s", e)
    finally:
        if client_ws.client_state == WebSocketState.CONNECTED:
            await client_ws.close()

# ── REST proxy (for room management etc.) ─────────────────────────────────────
@app.api_route("/{full_path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_rest(request: Request, full_path: str) -> Response:
    path = "/" + full_path
    upstream = next((u for p, u in REST_ROUTES if path.startswith(p)), None)
    if not upstream:
        raise HTTPException(status_code=404, detail=f"No route for {path}")
    url = upstream.rstrip("/") + (path[4:] if path.startswith("/api") else path)
    if request.url.query:
        url += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    try:
        r = await _client.request(request.method, url, headers=headers, content=await request.body())
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Upstream unavailable")
    skip = {"transfer-encoding", "connection", "keep-alive"}
    return Response(content=r.content, status_code=r.status_code,
                    headers={k: v for k, v in r.headers.items() if k.lower() not in skip},
                    media_type=r.headers.get("content-type"))

@app.get("/health")
async def health():
    checks = {"gateway": "ok"}
    for name, url in [("chat-service", CHAT_SERVICE_URL), ("metrics-service", METRICS_SERVICE_URL)]:
        try:
            r = await _client.get(f"{url}/health", timeout=3.0)
            checks[name] = "ok" if r.status_code == 200 else "degraded"
        except:
            checks[name] = "unreachable"
    return JSONResponse({"status": "ok" if all(v=="ok" for v in checks.values()) else "degraded", "services": checks})
