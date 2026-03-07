"""registry/health_monitor.py — polls all registered services for health."""
import asyncio, logging
from datetime import datetime, timezone
import httpx
from sqlalchemy import select, update
from database import AsyncSessionLocal
from models import RegisteredService, ServiceStatus

logger = logging.getLogger("health_monitor")
POLL_INTERVAL = 30

async def run_health_monitor() -> None:
    logger.info("Health monitor started (%ss interval)", POLL_INTERVAL)
    while True:
        try:
            await asyncio.sleep(POLL_INTERVAL)
            await _poll_all()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Monitor error: %s", e)

async def _poll_all():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RegisteredService).where(RegisteredService.is_active == True))  # noqa
        services = result.scalars().all()
    async with httpx.AsyncClient(timeout=5.0) as client:
        for svc in services:
            await _check(svc, client)

async def _check(service: RegisteredService, client: httpx.AsyncClient):
    async with AsyncSessionLocal() as db:
        try:
            r = await client.get(service.health_url)
            is_ok = r.status_code == 200
            await db.execute(
                update(RegisteredService).where(RegisteredService.id == service.id)
                .values(status=ServiceStatus.ACTIVE if is_ok else ServiceStatus.ERROR,
                        last_seen=datetime.now(timezone.utc) if is_ok else service.last_seen)
            )
            await db.commit()
            if not is_ok:
                logger.warning("'%s' health failed (HTTP %s) — hook agent here", service.name, r.status_code)
                # teammates: await trigger_agent_for_service(service.id, "health_check_failed")
        except httpx.ConnectError:
            logger.error("'%s' unreachable at %s", service.name, service.health_url)
            await db.execute(update(RegisteredService).where(RegisteredService.id == service.id).values(status=ServiceStatus.ERROR))
            await db.commit()
