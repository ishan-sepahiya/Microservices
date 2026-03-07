import logging, httpx
from config import settings
logger = logging.getLogger("startup")

async def register_with_agent():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.agent_service_url}/control/services/register",
                headers={"X-Agent-Api-Key": settings.agent_api_key},
                json={"name": "product-service", "service_type": "rest",
                      "base_url": "http://product-service:8001", "health_url": "http://product-service:8001/health",
                      "instructions": "Monitor inventory. Alert if any active product stock reaches 0. Alert on 5xx errors."},
            )
            logger.info("Registered with agent (HTTP %s)", r.status_code)
    except Exception as e:
        logger.warning("Could not register with agent: %s (continuing anyway)", e)
