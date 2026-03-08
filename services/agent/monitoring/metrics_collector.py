"""
monitoring/metrics_collector.py
Fetches REAL metrics from each microservice's /metrics/otel endpoint.
Zero simulation — all data comes from live services.
"""
import os, logging, asyncio, concurrent.futures
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("metrics_collector")

SERVICE_ENDPOINTS = {
    "product_service": os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001"),
    "payment_service": os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002"),
    "chat_service":    os.getenv("CHAT_SERVICE_URL",    "http://chat-service:8011"),
    "metrics_service": os.getenv("METRICS_SERVICE_URL", "http://metrics-service:8012"),
}


async def _fetch_one(service_name: str, base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url.rstrip('/')}/metrics/otel")
            if r.status_code == 200:
                d = r.json()
                return {
                    "latency_ms":     d.get("avg_latency_ms", 0),
                    "error_rate":     d.get("error_rate", 0.0),
                    "request_rate":   d.get("request_rate", 0),
                    "status":         d.get("status", "healthy"),
                    "total_requests": d.get("total_requests", 0),
                    "total_errors":   d.get("total_errors", 0),
                    "uptime_seconds": d.get("uptime_seconds", 0),
                }
            logger.warning("'%s' /metrics/otel returned HTTP %s", service_name, r.status_code)
            return _dead(f"HTTP {r.status_code}")
    except httpx.ConnectError:
        logger.error("Cannot reach '%s' at %s", service_name, base_url)
        return _dead("unreachable")
    except Exception as e:
        logger.error("Fetch failed for '%s': %s", service_name, e)
        return _dead(str(e))


def _dead(reason: str) -> dict:
    return {"latency_ms": 9999, "error_rate": 1.0,
            "request_rate": 0, "status": "unreachable", "error": reason}


async def _collect_all() -> dict:
    tasks = {name: _fetch_one(name, url) for name, url in SERVICE_ENDPOINTS.items()}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    out = {}
    for name, result in zip(tasks.keys(), results):
        out[name] = _dead(str(result)) if isinstance(result, Exception) else result
    logger.info("Collected live metrics for %d services", len(out))
    return out


def collect_metrics(scenario: str = "normal") -> dict:
    """sync wrapper — scenario param kept for API compat, always returns live data"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _collect_all()).result(timeout=15)
        return loop.run_until_complete(_collect_all())
    except Exception as e:
        logger.error("collect_metrics failed: %s", e)
        return {}
