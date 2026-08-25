"""Request tracing and metrics collection."""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RequestTrace:
    """Tracks a single request through the system."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    phone: str = ""
    channel: str = ""
    intent: str = ""
    start_time: float = field(default_factory=time.monotonic)
    latency_ms: float = 0
    llm_calls: int = 0
    mcp_calls: int = 0
    cache_hits: int = 0
    error: Optional[str] = None

    def finish(self) -> None:
        """Mark the trace as complete, calculating latency."""
        self.latency_ms = round((time.monotonic() - self.start_time) * 1000, 1)


class MetricsCollector:
    """Collects and aggregates request metrics in memory."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._traces: List[RequestTrace] = []
        self._lock = threading.Lock()
        self._max_traces = max_traces
        self._total_requests = 0
        self._total_errors = 0
        self._intent_counts: Dict[str, int] = {}

    def record(self, trace: RequestTrace) -> None:
        """Record a completed request trace."""
        with self._lock:
            self._traces.append(trace)
            if len(self._traces) > self._max_traces:
                self._traces = self._traces[-self._max_traces :]
            self._total_requests += 1
            if trace.error:
                self._total_errors += 1
            if trace.intent:
                self._intent_counts[trace.intent] = (
                    self._intent_counts.get(trace.intent, 0) + 1
                )

    def summary(self) -> dict:
        """Return aggregated metrics summary."""
        with self._lock:
            traces = list(self._traces)
            total = self._total_requests
            errors = self._total_errors
            intents = dict(self._intent_counts)

        if not traces:
            return {
                "total_requests": 0,
                "total_errors": 0,
                "avg_latency_ms": 0,
                "intents": {},
                "recent_traces": [],
            }

        latencies = [t.latency_ms for t in traces if t.latency_ms > 0]
        avg_latency = round(sum(latencies) / max(len(latencies), 1), 1)
        total_llm = sum(t.llm_calls for t in traces)
        total_mcp = sum(t.mcp_calls for t in traces)
        total_cache = sum(t.cache_hits for t in traces)

        recent = [
            {
                "request_id": t.request_id,
                "phone": t.phone[-4:] if t.phone else "",
                "intent": t.intent,
                "latency_ms": t.latency_ms,
                "error": t.error,
            }
            for t in traces[-10:]
        ]

        return {
            "total_requests": total,
            "total_errors": errors,
            "avg_latency_ms": avg_latency,
            "total_llm_calls": total_llm,
            "total_mcp_calls": total_mcp,
            "total_cache_hits": total_cache,
            "intents": intents,
            "recent_traces": recent,
        }
