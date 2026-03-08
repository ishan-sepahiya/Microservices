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
        result = await db.execute(
            select(RegisteredService).where(RegisteredService.is_active == True)  # noqa
        )
        services = result.scalars().all()
    if not services:
        logger.debug("No registered services to poll yet")
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        for svc in services:
            await _check(svc, client)


async def _check(service: RegisteredService, client: httpx.AsyncClient):
    async with AsyncSessionLocal() as db:
        try:
            r = await client.get(service.health_url)
            if r.status_code == 200:
                # Parse health body if available
                try:
                    body = r.json()
                    svc_status = body.get("status", "ok")
                    new_status = ServiceStatus.HEALTHY if svc_status in ("ok", "healthy") else ServiceStatus.DEGRADED
                except Exception:
                    new_status = ServiceStatus.HEALTHY

                await db.execute(
                    update(RegisteredService)
                    .where(RegisteredService.id == service.id)
                    .values(
                        status=new_status,
                        last_seen=datetime.now(timezone.utc),
                    )
                )
                logger.debug("'%s' → %s", service.name, new_status.value)
            else:
                await db.execute(
                    update(RegisteredService)
                    .where(RegisteredService.id == service.id)
                    .values(status=ServiceStatus.DEGRADED)
                )
                logger.warning("'%s' health returned HTTP %s", service.name, r.status_code)
            await db.commit()
        except httpx.ConnectError:
            logger.error("'%s' unreachable at %s", service.name, service.health_url)
            await db.execute(
                update(RegisteredService)
                .where(RegisteredService.id == service.id)
                .values(status=ServiceStatus.DOWN)
            )
            await db.commit()
        except Exception as e:
            logger.error("Error checking '%s': %s", service.name, e)
