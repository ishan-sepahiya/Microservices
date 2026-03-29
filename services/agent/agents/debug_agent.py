"""
debug_agent.py
Fetches REAL logs from each service's /logs/recent endpoint.
Zero hardcoded/simulated logs.
"""
import os
import logging
import httpx
from utils.webhook_client import trigger_debug_webhook
from utils.llm_interface import call_llm
from utils.prompt_templates import build_debug_prompt
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("debug_agent")

SERVICE_URLS = {
    "product_service": os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001"),
    "payment_service": os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002"),
    "chat_service":    os.getenv("CHAT_SERVICE_URL",    "http://chat-service:8011"),
    "metrics_service": os.getenv("METRICS_SERVICE_URL", "http://metrics-service:8012"),
}


async def _fetch_logs(service: str) -> list[str]:
    base = SERVICE_URLS.get(service)
    if not base:
        return [f"ERROR No URL configured for service: {service}"]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{base.rstrip('/')}/logs/recent")
            if r.status_code == 200:
                data = r.json()
                return data.get("logs", [f"INFO {service} returned empty log list"])
            return [f"ERROR /logs/recent returned HTTP {r.status_code}"]
    except httpx.ConnectError:
        return [f"ERROR Cannot reach {service} at {base}"]
    except Exception as e:
        return [f"ERROR Log fetch failed: {e}"]


async def _analyse(service: str, logs: list) -> dict:
    import json
    raw = await call_llm(build_debug_prompt(service, logs))
    try:
        s = raw.find("{")
        e = raw.rfind("}") + 1
        if s != -1 and e > s:
            return json.loads(raw[s:e])
    except Exception:
        pass
    return {"service": service, "root_cause": "LLM parse failed", "recommendation": "Manual investigation required"}


async def run_debug_agent(service: str) -> dict:
    logger.info("[DebugAgent] Analyzing service: %s", service)
    logs = await _fetch_logs(service)
    analysis = await _analyse(service, logs)
    result = trigger_debug_webhook(service=service, analysis=analysis)
    return {
        "agent": "debug",
        "service": service,
        "analysis": analysis,
        "logs_count": len(logs),
        "webhook_result": result,
    }


def run_debug_agent(service: str, use_llm: bool = True) -> dict:
    logger.info("[DebugAgent] Fetching live logs for: %s", service)
    logs = _fetch_logs(service)
    logger.info("[DebugAgent] Got %d log entries", len(logs))
    for line in logs:
        logger.debug("  %s", line)

    analysis = _analyse(service, logs) if use_llm else {
        "service": service,
        "root_cause": "LLM disabled",
        "recommendation": "Enable LLM for analysis",
    }
    logger.info("[DebugAgent] root_cause=%s", analysis.get("root_cause"))
    result = trigger_debug_webhook(service=service, analysis=analysis)

    return {"agent": "debug", "service": service, "logs": logs,
            "analysis": analysis, "webhook_result": result}
