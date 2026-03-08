from monitoring.metrics_collector import collect_metrics
from utils.llm_interface import analyze_metrics
import logging

logger = logging.getLogger("health_agent")

def run_health_agent(scenario: str = "normal") -> dict:
    logger.info("[HealthAgent] Running live health check")
    metrics = collect_metrics(scenario)
    logger.info("[HealthAgent] Collected metrics for %d services", len(metrics))
    decisions = analyze_metrics(metrics)
    for d in decisions:
        logger.info("  → %s: %s — %s", d["service"], d["action"], d["reason"])
    return {"metrics": metrics, "decisions": decisions, "scenario": scenario}
