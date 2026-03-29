import os
import json
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from orchestrator.langgraph_flow import run_workflow
from monitoring.metrics_collector import collect_metrics

st.set_page_config(page_title="AI DevOps Monitor", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
.metric-card{background:#1e1e2e;border-radius:12px;padding:16px;margin:8px 0;border-left:4px solid #7c3aed}
.status-healthy{color:#22c55e;font-weight:bold}.status-warning{color:#f59e0b;font-weight:bold}.status-critical{color:#ef4444;font-weight:bold}
.action-badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:bold}
.action-HEALTHY{background:#166534;color:#bbf7d0}.action-SCALE{background:#1d4ed8;color:#bfdbfe}
.action-RESTART{background:#92400e;color:#fde68a}.action-ROLLBACK{background:#7f1d1d;color:#fecaca}
.action-DEBUG{background:#4c1d95;color:#e9d5ff}
</style>""", unsafe_allow_html=True)

for k, v in [("workflow_result", None), ("last_scenario", None), ("run_history", []), ("live_metrics", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.live_metrics is None:
    with st.spinner("Fetching live metrics..."):
        st.session_state.live_metrics = collect_metrics("normal")

col_title, col_status = st.columns([4, 1])
with col_title:
    st.title("🤖 AI DevOps Monitoring Agent")
    st.caption("LangGraph · Ollama (Mistral) · n8n Webhooks · OpenTelemetry")
with col_status:
    st.metric("Agent Status", "🟢 Online")

st.divider()

with st.sidebar:
    st.header("⚙️ Configuration")
    st.code(f"Ollama: {os.getenv('OLLAMA_URL','http://ollama:11434/api/generate')}", language=None)
    st.caption(f"OTel: live /metrics/otel per service")
    st.divider()
    st.subheader("📋 Run History")
    if st.session_state.run_history:
        for i, h in enumerate(reversed(st.session_state.run_history[-8:])):
            st.caption(f"#{len(st.session_state.run_history)-i} `{h['scenario']}` — {h['decisions']} decisions")
    else:
        st.caption("No runs yet.")
    if st.button("🔄 Refresh Live Metrics", use_container_width=True):
        st.session_state.live_metrics = collect_metrics("normal")
        st.rerun()

st.subheader("📊 Live Service Metrics")
metrics = st.session_state.live_metrics or {}
if metrics:
    cols = st.columns(len(metrics))
    for col, (svc, data) in zip(cols, metrics.items()):
        with col:
            status = data.get("status", "unknown")
            latency = data.get("latency_ms", 0)
            error_rate = data.get("error_rate", 0)
            req_rate = data.get("request_rate", 0)
            if status == "healthy" and latency < 300 and error_rate < 0.03:
                cls, icon = "status-healthy", "✅"
            elif status in ("crashed", "unreachable", "deployment_failed") or error_rate > 0.07:
                cls, icon = "status-critical", "🔴"
            else:
                cls, icon = "status-warning", "⚠️"
            st.markdown(f"**{icon} {svc.replace('_',' ').title()}**")
            st.metric("Latency", f"{latency} ms")
            st.metric("Error Rate", f"{error_rate:.2%}")
            st.metric("Req Rate", f"{req_rate}/s")
            st.markdown(f'<span class="{cls}">{status.upper()}</span>', unsafe_allow_html=True)
else:
    st.warning("No metrics — are services running?")

st.divider()
st.subheader("🎮 Trigger Agent Workflow")

def trigger(scenario):
    with st.spinner(f"Running LangGraph: **{scenario}**..."):
        result = run_workflow(scenario=scenario)
        st.session_state.workflow_result = result
        st.session_state.last_scenario = scenario
        st.session_state.live_metrics = result.get("metrics") or st.session_state.live_metrics
        st.session_state.run_history.append({
            "scenario": scenario,
            "decisions": len(result.get("decisions", [])),
            "actions": len(result.get("actions_taken", [])),
        })

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📈 Traffic Spike", use_container_width=True, type="primary"): trigger("traffic_spike"); st.rerun()
with c2:
    if st.button("💥 Service Crash", use_container_width=True, type="primary"): trigger("service_crash"); st.rerun()
with c3:
    if st.button("🚫 Deploy Failure", use_container_width=True, type="primary"): trigger("deployment_failure"); st.rerun()
with c4:
    if st.button("✅ Normal", use_container_width=True): trigger("normal"); st.rerun()

if st.session_state.workflow_result:
    st.divider()
    result = st.session_state.workflow_result
    st.subheader(f"🧠 Agent Decisions — `{st.session_state.last_scenario}`")
    decisions = result.get("decisions", [])
    actions_taken = result.get("actions_taken", [])
    errors = result.get("errors", [])
    k1, k2, k3 = st.columns(3)
    k1.metric("Decisions", len(decisions))
    k2.metric("Actions Taken", len(actions_taken))
    k3.metric("Errors", len(errors))
    if decisions:
        st.markdown("#### 📋 LLM Decisions")
        dcols = st.columns(min(len(decisions), 3))
        for i, d in enumerate(decisions):
            with dcols[i % len(dcols)]:
                action = d.get("action", "HEALTHY")
                st.markdown(f"""<div class="metric-card"><strong>{d.get('service','?').replace('_',' ').title()}</strong><br>
                    <span class="action-badge action-{action}">{action}</span><br>
                    <small style="color:#94a3b8">{d.get('reason','—')}</small></div>""", unsafe_allow_html=True)
    if actions_taken:
        st.markdown("#### ⚡ Actions Executed")
        for a in actions_taken:
            icon = {"scaling":"📈","deployment":"🔄","debug":"🔍"}.get(a.get("agent",""), "⚙️")
            st.success(f"{icon} **{a.get('agent','?').upper()}** → `{a.get('service','?')}` | webhook: `{a.get('webhook_result',{}).get('status','?')}`")
    if errors:
        for e in errors: st.error(e)
    with st.expander("🗂️ Raw State"):
        st.json(result)

st.divider()
st.caption("AI DevOps Agent · LangGraph + Ollama (Mistral) + OpenTelemetry + Streamlit")
