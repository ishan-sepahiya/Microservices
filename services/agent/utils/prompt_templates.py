import json

def build_analysis_prompt(metrics: dict) -> str:
    return f"""You are an expert DevOps AI agent monitoring production microservices.

Analyze the following LIVE telemetry and decide the action for each service.

METRICS:
{json.dumps(metrics, indent=2)}

RULES:
- latency_ms > 400 OR request_rate > 250  → SCALE
- error_rate > 0.05 OR status = "crashed" OR status = "unreachable" → RESTART
- status = "deployment_failed"             → ROLLBACK
- error_rate > 0.10 AND latency_ms > 600  → DEBUG
- otherwise                               → HEALTHY

Respond ONLY with a JSON array. No markdown. No explanation.

[
  {{
    "service": "<name>",
    "action": "<HEALTHY|SCALE|RESTART|ROLLBACK|DEBUG>",
    "reason": "<brief reason citing actual metric values>"
  }}
]"""

def build_debug_prompt(service: str, logs: list) -> str:
    return f"""You are a DevOps debugging agent.

Analyze the following LIVE logs for service "{service}" and identify the root cause.

LOGS:
{chr(10).join(logs)}

Respond ONLY with JSON. No markdown.

{{
  "service": "{service}",
  "root_cause": "<identified root cause>",
  "recommendation": "<suggested fix>"
}}"""

def build_scaling_rationale_prompt(service: str, metrics: dict) -> str:
    return f"DevOps scaling needed for {service}. Metrics: {json.dumps(metrics)}. Explain in one sentence why scaling is correct."
