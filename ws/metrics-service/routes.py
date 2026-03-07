import asyncio, json, random, logging
from datetime import datetime, timezone
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import MetricOut, MetricSnapshot

logger = logging.getLogger("metrics")
router = APIRouter(tags=["Metrics"])

WATCHED = ["product-service", "payment-service", "chat-service", "agent"]

@router.get("/metrics/history", response_model=list[MetricOut])
async def history(service_name: str | None = Query(default=None), limit: int = Query(default=100, le=1000), db: AsyncSession = Depends(get_db)):
    q = select(MetricSnapshot).order_by(desc(MetricSnapshot.recorded_at)).limit(limit)
    if service_name: q = q.where(MetricSnapshot.service_name == service_name)
    result = await db.execute(q)
    return list(result.scalars().all())

@router.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket, services: str = Query(default="all"), interval: float = Query(default=2.0), db: AsyncSession = Depends(get_db)):
    """Connect: ws://host/ws/metrics?services=product-service,payment-service&interval=2"""
    await ws.accept()
    svc_list = [s.strip() for s in services.split(",")] if services != "all" else WATCHED
    try:
        while True:
            snapshots = []
            for svc in svc_list:
                cpu = round(random.uniform(5, 95), 1)
                mem = round(random.uniform(20, 80), 1)
                snap = MetricSnapshot(service_name=svc, cpu_percent=cpu, memory_percent=mem,
                                      request_count=random.randint(0,100), error_count=random.randint(0,3))
                db.add(snap)
                snapshots.append({"service": svc, "cpu_percent": cpu, "memory_percent": mem,
                                   "request_count": snap.request_count, "error_count": snap.error_count})
            await db.flush()
            await ws.send_text(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "metrics": snapshots}))
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        logger.info("Metrics client disconnected")
