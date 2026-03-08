import logging
import httpx
from config import settings

logger = logging.getLogger("startup")


async def register_with_agent():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.agent_service_url}/control/register",
                headers={"X-Control-Key": settings.agent_api_key},
                json={
                    "name": "payment-service",
                    "service_type": "rest",
                    "base_url": "http://payment-service:8002",
                    "health_url": "http://payment-service:8002/health",
                    "description": "Handles payment processing and transaction management",
                    "instructions": "Alert immediately on any payment failure. Restart if error_rate > 2%. Rollback on deployment_failed.",
                },
            )
            logger.info("Registered with agent (HTTP %s)", r.status_code)
    except Exception as e:
        logger.warning("Could not register with agent: %s (continuing anyway)", e)
