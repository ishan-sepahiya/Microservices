from datetime import datetime, timezone
import logging
from utils.webhook_client import trigger_restart_webhook, trigger_rollback_webhook

logger = logging.getLogger("deployment_agent")
_log = []

def _record(service, action, result):
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(),
             "service": service, "action": action, "result": result}
    _log.append(entry)
    logger.info("[DeploymentAgent] %s → %s | %s", action, service, result.get("status"))
    return entry

def run_restart_agent(service: str) -> dict:
    result = trigger_restart_webhook(service=service)
    return {"agent": "deployment", "action": "restart", "service": service,
            "webhook_result": result, "log_entry": _record(service, "RESTART", result)}

def run_rollback_agent(service: str) -> dict:
    result = trigger_rollback_webhook(service=service)
    return {"agent": "deployment", "action": "rollback", "service": service,
            "webhook_result": result, "log_entry": _record(service, "ROLLBACK", result)}

def get_deployment_log() -> list:
    return list(_log)
