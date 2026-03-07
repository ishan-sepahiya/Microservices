from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from agents.health_agent import run_health_agent
from agents.scaling_agent import run_scaling_agent
from agents.deployment_agent import run_restart_agent, run_rollback_agent
from agents.debug_agent import run_debug_agent
import logging

logger = logging.getLogger("orchestrator")

class AgentState(TypedDict):
    scenario: str
    metrics: dict
    decisions: List[dict]
    actions_taken: List[dict]
    errors: List[str]

def health_node(state: AgentState) -> AgentState:
    logger.info("[Orchestrator] → health_node")
    try:
        result = run_health_agent(scenario=state.get("scenario", "normal"))
        return {**state, "metrics": result["metrics"], "decisions": result["decisions"]}
    except Exception as e:
        err = f"health_node error: {e}"
        logger.error(err)
        return {**state, "metrics": {}, "decisions": [{"service": "unknown", "action": "HEALTHY", "reason": err}],
                "errors": state.get("errors", []) + [err]}

def scaling_node(state: AgentState) -> AgentState:
    logger.info("[Orchestrator] → scaling_node")
    actions = list(state.get("actions_taken", []))
    for d in state.get("decisions", []):
        if d.get("action") == "SCALE":
            actions.append(run_scaling_agent(service=d["service"], metrics=state.get("metrics", {})))
    return {**state, "actions_taken": actions}

def deployment_node(state: AgentState) -> AgentState:
    logger.info("[Orchestrator] → deployment_node")
    actions = list(state.get("actions_taken", []))
    for d in state.get("decisions", []):
        if d.get("action") == "RESTART":
            actions.append(run_restart_agent(service=d["service"]))
        elif d.get("action") == "ROLLBACK":
            actions.append(run_rollback_agent(service=d["service"]))
    return {**state, "actions_taken": actions}

def debug_node(state: AgentState) -> AgentState:
    logger.info("[Orchestrator] → debug_node")
    actions = list(state.get("actions_taken", []))
    for d in state.get("decisions", []):
        if d.get("action") == "DEBUG":
            actions.append(run_debug_agent(service=d["service"]))
    return {**state, "actions_taken": actions}

def healthy_node(state: AgentState) -> AgentState:
    logger.info("[Orchestrator] → healthy_node: all services healthy")
    return state

def route(state: AgentState) -> str:
    actions = {d.get("action", "HEALTHY").upper() for d in state.get("decisions", [])}
    logger.info("[Orchestrator] routing on actions: %s", actions)
    if "DEBUG" in actions: return "debug"
    if "RESTART" in actions or "ROLLBACK" in actions: return "deployment"
    if "SCALE" in actions: return "scaling"
    return "healthy"

def build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("health", health_node)
    g.add_node("scaling", scaling_node)
    g.add_node("deployment", deployment_node)
    g.add_node("debug", debug_node)
    g.add_node("healthy", healthy_node)
    g.set_entry_point("health")
    g.add_conditional_edges("health", route, {"scaling": "scaling", "deployment": "deployment", "debug": "debug", "healthy": "healthy"})
    for n in ["scaling", "deployment", "debug", "healthy"]:
        g.add_edge(n, END)
    return g.compile()

_graph = None
def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

def run_workflow(scenario: str = "normal") -> AgentState:
    logger.info("="*50)
    logger.info("[Orchestrator] Starting workflow — scenario: %s", scenario)
    final = get_graph().invoke({"scenario": scenario, "metrics": {}, "decisions": [], "actions_taken": [], "errors": []})
    logger.info("[Orchestrator] Done. decisions=%d actions=%d errors=%d",
                len(final.get("decisions",[])), len(final.get("actions_taken",[])), len(final.get("errors",[])))
    return final
