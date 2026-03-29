import os
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("webhook")

N8N_SCALE_WEBHOOK    = os.getenv("N8N_SCALE_WEBHOOK", "")
N8N_RESTART_WEBHOOK  = os.getenv("N8N_RESTART_WEBHOOK", "")
N8N_ROLLBACK_WEBHOOK = os.getenv("N8N_ROLLBACK_WEBHOOK", "")
N8N_DEBUG_WEBHOOK    = os.getenv("N8N_DEBUG_WEBHOOK", "")


def _send(url: str, payload: dict, label: str) -> dict:
    if not url:
        logger.info("[Webhook] %s not configured — simulating. payload=%s", label, json.dumps(payload))
        return {"status": "simulated", "label": label, "payload": payload}
    try:
        # Note: This is a sync function. For async context, use _send_async instead.
        import requests
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return {"status": "success", "code": r.status_code, "body": r.text}
    except Exception as e:
        logger.error("[Webhook] %s error: %s", label, e)
        return {"status": "error", "error": str(e)}


async def _send_async(url: str, payload: dict, label: str) -> dict:
    """Async version of _send for use in async contexts"""
    if not url:
        logger.info("[Webhook] %s not configured — simulating. payload=%s", label, json.dumps(payload))
        return {"status": "simulated", "label": label, "payload": payload}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return {"status": "success", "code": r.status_code, "body": r.text}
    except Exception as e:
        logger.error("[Webhook] %s error: %s", label, e)
        return {"status": "error", "error": str(e)}


def trigger_scale_webhook(service: str, replicas: int = 3) -> dict:
    return _send(N8N_SCALE_WEBHOOK, {"service": service, "replicas": replicas}, "SCALE")

def trigger_restart_webhook(service: str) -> dict:
    return _send(N8N_RESTART_WEBHOOK, {"service": service, "action": "restart"}, "RESTART")

def trigger_rollback_webhook(service: str) -> dict:
    return _send(N8N_ROLLBACK_WEBHOOK, {"service": service, "action": "rollback"}, "ROLLBACK")

def trigger_debug_webhook(service: str, analysis: dict) -> dict:
    return _send(N8N_DEBUG_WEBHOOK, {"service": service, "debug_analysis": analysis}, "DEBUG")
