"""
otel_middleware.py — OpenTelemetry instrumentation for FastAPI services.
Tracks: request count, error count, latency.
Exposes: GET /metrics/otel  — live metrics for the agent
         GET /logs/recent   — last 200 log lines for the debug agent
"""
import time, logging, threading
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from opentelemetry import trace, metrics as otel_metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

import os

OTEL_ENDPOINT   = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
SERVICE_NAME    = os.getenv("OTEL_SERVICE_NAME", "unknown-service")
START_TIME      = time.time()

# ── In-memory metrics counters (thread-safe) ──────────────────────────────────
_lock           = threading.Lock()
_total_requests = 0
_total_errors   = 0
_latencies      = deque(maxlen=500)   # rolling window

# ── In-memory log ring buffer ─────────────────────────────────────────────────
_log_buffer: deque = deque(maxlen=200)

class _BufferHandler(logging.Handler):
    def emit(self, record):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _log_buffer.append(f"{record.levelname:<5} {ts} {record.getMessage()}")

_buf_handler = _BufferHandler()
_buf_handler.setLevel(logging.WARNING)   # capture WARN and above into ring buffer
logging.getLogger().addHandler(_buf_handler)


def setup_otel(app: FastAPI, service_name: str = SERVICE_NAME) -> None:
    """Call this in main.py after creating the FastAPI app."""
    resource = Resource.create({"service.name": service_name})

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    try:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
        )
    except Exception:
        pass  # collector not up yet — traces disabled, metrics still work
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    try:
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
            export_interval_millis=15_000,
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        otel_metrics.set_meter_provider(meter_provider)
    except Exception:
        pass

    # FastAPI middleware
    @app.middleware("http")
    async def _otel_middleware(request: Request, call_next):
        global _total_requests, _total_errors
        t0 = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        with _lock:
            _total_requests += 1
            _latencies.append(elapsed_ms)
            if response.status_code >= 500:
                _total_errors += 1
                _log_buffer.append(
                    f"ERROR {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
                    f"HTTP {response.status_code} {request.method} {request.url.path} ({elapsed_ms:.1f}ms)"
                )

        return response

    # /metrics/otel endpoint — what the agent polls
    @app.get("/metrics/otel", tags=["Observability"], include_in_schema=False)
    async def metrics_otel():
        with _lock:
            total_req = _total_requests
            total_err = _total_errors
            lats = list(_latencies)

        avg_lat   = round(sum(lats) / len(lats), 1) if lats else 0
        err_rate  = round(total_err / total_req, 4) if total_req > 0 else 0.0
        req_rate  = round(total_req / max(time.time() - START_TIME, 1), 2)
        status    = "healthy"
        if err_rate > 0.10:  status = "degraded"
        if err_rate > 0.30:  status = "crashed"

        return {
            "service":         service_name,
            "status":          status,
            "avg_latency_ms":  avg_lat,
            "error_rate":      err_rate,
            "request_rate":    req_rate,
            "total_requests":  total_req,
            "total_errors":    total_err,
            "uptime_seconds":  round(time.time() - START_TIME, 1),
        }

    # /logs/recent endpoint — what the debug agent polls
    @app.get("/logs/recent", tags=["Observability"], include_in_schema=False)
    async def logs_recent():
        return {"service": service_name, "logs": list(_log_buffer)}
