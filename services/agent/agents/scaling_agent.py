from utils.webhook_client import trigger_scale_webhook
import logging

logger = logging.getLogger("scaling_agent")
DEFAULT_REPLICAS = 3

def run_scaling_agent(service: str, metrics: dict = None, replicas: int = DEFAULT_REPLICAS) -> dict:
    logger.info("[ScalingAgent] Scale-up for: %s", service)
    if metrics and service in metrics:
        m = metrics[service]
        latency, req_rate = m.get("latency_ms", 0), m.get("request_rate", 0)
        replicas = 5 if req_rate > 350 else (4 if req_rate > 250 or latency > 500 else DEFAULT_REPLICAS)
        logger.info("[ScalingAgent] latency=%dms rate=%d/s → %d replicas", latency, req_rate, replicas)
    result = trigger_scale_webhook(service=service, replicas=replicas)
    return {"agent": "scaling", "service": service, "replicas": replicas, "webhook_result": result}
