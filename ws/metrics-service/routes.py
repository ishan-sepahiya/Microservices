"""
routes.py — Metrics Service
- GET  /metrics/otel        → aggregated live metrics (polled by agent's metrics_collector)
- GET  /metrics/history     → historical snapshots from DB
- WS   /ws/metrics          → real-time stream from live service /metrics/otel endpoints
"""
import asyncio, json, logging, time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import get_db
from models import MetricOut, MetricSnapshot

logger = logging.getLogger("metrics")
router = APIRouter(tags=["Metrics"])

# Services to probe (maps display name → base URL from config)
SERVICE_MAP = {
    "product-service": settings.product_service_url,
    "payment-service": settings.payment_service_url,
    "chat-service":    settings.chat_service_url,
}


async def _probe_service(client: httpx.AsyncClient, name: str, base_url: str) -> dict:
    """Fetch /health from a service and build a metric snapshot from real data."""
    start = time.monotonic()
    try:
        r = await client.get(f"{base_url.rstrip('/')}/health")
        latency_ms = int((time.monotonic() - start) * 1000)
        if r.status_code == 200:
            body = r.json()
            svc_status = body.get("status", "ok")
            checks = body.get("checks", {})
            errors = sum(1 for v in checks.values() if "error" in str(v).lower())
            return {
                "service": name,
                "status": svc_status,
                "latency_ms": latency_ms,
                "http_status": 200,
                "error_count": errors,
                "checks": checks,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "service": name, "status": "degraded",
            "latency_ms": latency_ms, "http_status": r.status_code,
            "error_count": 1, "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.ConnectError:
        return {
            "service": name, "status": "unreachable",
            "latency_ms": 9999, "http_status": 0,
            "error_count": 1, "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "service": name, "status": "error",
            "latency_ms": 0, "http_status": 0,
            "error_count": 1, "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def _collect_all() -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [_probe_service(client, name, url) for name, url in SERVICE_MAP.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        r["service"]: r for r in results
        if not isinstance(r, Exception)
    }


# ── /metrics/otel — called by agent's monitoring/metrics_collector.py ─────────

@router.get("/metrics/otel")
async def otel_metrics():
    """
    Returns live aggregated metrics from all registered services.
    The agent's metrics_collector.py fetches this endpoint to get real data.
    """
    metrics = await _collect_all()
    # Flatten to the shape metrics_collector expects
    result = {}
    for svc_name, data in metrics.items():
        result[svc_name] = {
            "avg_latency_ms": data.get("latency_ms", 0),
            "error_rate": 0.0 if data.get("error_count", 0) == 0 else 0.1,
            "request_rate": 0,   # Would come from OTel spans in production
            "status": data.get("status", "unknown"),
            "http_status": data.get("http_status", 0),
            "checks": data.get("checks", {}),
            "total_requests": 0,
            "total_errors": data.get("error_count", 0),
            "uptime_seconds": 0,
        }
    logger.info("Served /metrics/otel for %d services", len(result))
    return result


# ── GET /metrics/history ───────────────────────────────────────────────────────

@router.get("/metrics/history", response_model=list[MetricOut])
async def history(
    service_name: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
):
    q = select(MetricSnapshot).order_by(desc(MetricSnapshot.recorded_at)).limit(limit)
    if service_name:
        q = q.where(MetricSnapshot.service_name == service_name)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── WS /ws/metrics — streams live probes ──────────────────────────────────────

@router.websocket("/ws/metrics")
async def ws_metrics(
    ws: WebSocket,
    services: str = Query(default="all"),
    interval: float = Query(default=5.0, ge=1.0, le=60.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams real health data polled from services.
    Connect: ws://host/ws/metrics?services=product-service,payment-service&interval=5
    """
    await ws.accept()
    requested = (
        [s.strip() for s in services.split(",")]
        if services != "all" else list(SERVICE_MAP.keys())
    )
    probe_map = {name: url for name, url in SERVICE_MAP.items() if name in requested}

    logger.info("WS client connected, streaming %d services every %.1fs", len(probe_map), interval)
    try:
        while True:
            async with httpx.AsyncClient(timeout=5.0) as client:
                tasks = [_probe_service(client, name, url) for name, url in probe_map.items()]
                probes = await asyncio.gather(*tasks, return_exceptions=True)

            snapshots = []
            for probe in probes:
                if isinstance(probe, Exception):
                    continue
                # Persist snapshot
                snap = MetricSnapshot(
                    service_name=probe["service"],
                    cpu_percent=0.0,         # OTel would populate this in production
                    memory_percent=0.0,
                    request_count=0,
                    error_count=probe.get("error_count", 0),
                )
                db.add(snap)
                snapshots.append({
                    "service": probe["service"],
                    "status": probe["status"],
                    "latency_ms": probe["latency_ms"],
                    "http_status": probe["http_status"],
                    "error_count": probe.get("error_count", 0),
                    "checks": probe.get("checks", {}),
                })
            await db.flush()

            await ws.send_text(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": snapshots,
            }))
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        logger.info("Metrics WS client disconnected")
    except Exception as e:
        logger.error("WS error: %s", e)
