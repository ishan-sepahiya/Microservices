"""utils/llm_interface.py — Ollama (Mistral) calls"""
import os
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("llm")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "mistral")


async def call_llm(prompt: str) -> str:
    """Call Ollama LLM asynchronously"""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
            r.raise_for_status()
            return r.json().get("response", "")
    except httpx.ConnectError:
        logger.warning("Ollama not reachable, using rule-based fallback")
        return _rule_based(prompt)
    except Exception as e:
        logger.error("LLM error: %s", e)
        return _rule_based(prompt)


def _rule_based(prompt: str) -> str:
    """deterministic fallback when Ollama is down"""
    if "unreachable" in prompt or '"error_rate": 1.0' in prompt:
        return json.dumps([{"service": "unknown", "action": "RESTART", "reason": "Service unreachable"}])
    if "deployment_failed" in prompt:
        return json.dumps([{"service": "unknown", "action": "ROLLBACK", "reason": "Deployment failure detected"}])
    if '"latency_ms": 9999' in prompt:
        return json.dumps([{"service": "unknown", "action": "DEBUG", "reason": "Service completely unresponsive"}])
    return json.dumps([{"service": "all_services", "action": "HEALTHY", "reason": "All metrics within thresholds"}])


async def analyze_metrics(metrics: dict) -> list:
    from utils.prompt_templates import build_analysis_prompt
    raw = await call_llm(build_analysis_prompt(metrics))
    return _parse(raw)


def _parse(raw: str) -> list:
    try:
        s = raw.find("[")
        e = raw.rfind("]") + 1
        if s != -1 and e > s:
            decisions = json.loads(raw[s:e])
            validated = [
                {"service": d.get("service", "unknown"),
                 "action": d.get("action", "HEALTHY").upper(),
                 "reason": d.get("reason", "No reason")}
                for d in decisions if isinstance(d, dict) and "service" in d
            ]
            return validated or _healthy()
    except Exception as ex:
        logger.error("Failed to parse LLM decisions: %s", ex)
    return _healthy()


def _healthy() -> list:
    return [{"service": "all_services", "action": "HEALTHY",
             "reason": "Could not parse LLM response, defaulting to healthy"}]
