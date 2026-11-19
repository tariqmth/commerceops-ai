
import math
import threading
from collections import deque


class MetricsCollector:
    """Thread-safe in-memory HTTP metrics collector."""

    def __init__(self, max_samples: int = 10000):
        self._lock = threading.Lock()
        self._total_requests = 0
        self._error_requests = 0
        self._total_latency_ms = 0.0
        self._latency_samples = deque(maxlen=max_samples)

    def record_request(self, status_code: int, duration_ms: float):
        """Record one completed HTTP request."""

        with self._lock:
            self._total_requests += 1
            self._total_latency_ms += duration_ms
            self._latency_samples.append(duration_ms)

            if status_code >= 400:
                self._error_requests += 1

    @staticmethod
    def _percentile(values: list, percentile: float):
        """Calculate a nearest-rank percentile."""

        if not values:
            return 0.0

        ordered = sorted(values)
        index = math.ceil(percentile * len(ordered)) - 1

        return round(ordered[max(0, index)], 2)

    def get_metrics(self, service_name: str) -> dict:
        """Return a snapshot of the collected metrics."""

        with self._lock:
            total = self._total_requests
            errors = self._error_requests
            latency_sum = self._total_latency_ms
            samples = list(self._latency_samples)

        average = latency_sum / total if total else 0.0

        return {
            "service": service_name,
            "total_requests": total,
            "successful_requests": total - errors,
            "error_requests": errors,
            "error_rate_percent": round(
                (errors / total) * 100, 2
            ) if total else 0.0,
            "average_latency_ms": round(average, 2),
            "p50_latency_ms": self._percentile(samples, 0.50),
            "p95_latency_ms": self._percentile(samples, 0.95),
            "p99_latency_ms": self._percentile(samples, 0.99),
            "slowest_request_ms": round(max(samples), 2) if samples else 0.0,
            "latency_sample_count": len(samples),
        }


# One collector per running application process.
metrics = MetricsCollector()
