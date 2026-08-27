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
    node_timings: Dict[str, float] = field(default_factory=dict)
    llm_calls: int = 0
    mcp_calls: int = 0
    cache_hits: int = 0
    error: Optional[str] = None

    def finish(self) -> None:
        """Mark the trace as complete, calculating latency."""
        self.latency_ms = round((time.monotonic() - self.start_time) * 1000, 1)


def _percentile(data: List[float], p: float) -> float:
    """Calculate the p-th percentile of a sorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return round(sorted_data[-1], 1)
    d = k - f
    return round(sorted_data[f] + d * (sorted_data[c] - sorted_data[f]), 1)


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

    def latency_report(self) -> dict:
        """Return detailed latency report with percentiles."""
        with self._lock:
            traces = list(self._traces)

        if not traces:
            return {
                "total_requests": 0,
                "percentiles": {"p50": 0, "p95": 0, "p99": 0},
                "avg_latency_ms": 0,
                "min_latency_ms": 0,
                "max_latency_ms": 0,
                "by_intent": {},
                "by_node": {},
            }

        latencies = [t.latency_ms for t in traces if t.latency_ms > 0]

        # Aggregate node timings
        node_latencies: Dict[str, List[float]] = {}
        for t in traces:
            for node, dur in t.node_timings.items():
                node_latencies.setdefault(node, []).append(dur)

        by_node = {}
        for node, durations in node_latencies.items():
            by_node[node] = {
                "count": len(durations),
                "avg_ms": round(sum(durations) / len(durations), 1),
                "p50": _percentile(durations, 50),
                "p95": _percentile(durations, 95),
                "min_ms": round(min(durations), 1),
                "max_ms": round(max(durations), 1),
            }

        # Aggregate by intent
        intent_latencies: Dict[str, List[float]] = {}
        for t in traces:
            if t.intent and t.latency_ms > 0:
                intent_latencies.setdefault(t.intent, []).append(t.latency_ms)

        by_intent = {}
        for intent, durations in intent_latencies.items():
            by_intent[intent] = {
                "count": len(durations),
                "avg_ms": round(sum(durations) / len(durations), 1),
                "p50": _percentile(durations, 50),
                "p95": _percentile(durations, 95),
            }

        return {
            "total_requests": len(latencies),
            "percentiles": {
                "p50": _percentile(latencies, 50),
                "p95": _percentile(latencies, 95),
                "p99": _percentile(latencies, 99),
            },
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
            "min_latency_ms": round(min(latencies), 1),
            "max_latency_ms": round(max(latencies), 1),
            "by_intent": by_intent,
            "by_node": by_node,
        }

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
