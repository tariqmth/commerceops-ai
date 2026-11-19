
from integrations.metrics import MetricsCollector


def test_metrics_record_successful_request():
    collector = MetricsCollector()

    collector.record_request(200, 50.0)

    result = collector.get_metrics("test-service")

    assert result["total_requests"] == 1
    assert result["successful_requests"] == 1
    assert result["error_requests"] == 0
    assert result["average_latency_ms"] == 50.0


def test_metrics_record_failed_request():
    collector = MetricsCollector()

    collector.record_request(200, 50.0)
    collector.record_request(503, 100.0)

    result = collector.get_metrics("test-service")

    assert result["total_requests"] == 2
    assert result["successful_requests"] == 1
    assert result["error_requests"] == 1
    assert result["error_rate_percent"] == 50.0


def test_metrics_calculate_average_latency():
    collector = MetricsCollector()

    collector.record_request(200, 20.0)
    collector.record_request(200, 40.0)
    collector.record_request(200, 60.0)

    result = collector.get_metrics("test-service")

    assert result["average_latency_ms"] == 40.0


def test_metrics_calculate_latency_percentiles():
    collector = MetricsCollector()

    for duration in range(1, 101):
        collector.record_request(200, float(duration))

    result = collector.get_metrics("test-service")

    assert result["p50_latency_ms"] == 50.0
    assert result["p95_latency_ms"] == 95.0
    assert result["p99_latency_ms"] == 99.0
    assert result["slowest_request_ms"] == 100.0


def test_metrics_limit_latency_samples():
    collector = MetricsCollector(max_samples=3)

    for duration in (10.0, 20.0, 30.0, 40.0):
        collector.record_request(200, duration)

    result = collector.get_metrics("test-service")

    assert result["total_requests"] == 4
    assert result["latency_sample_count"] == 3
    assert result["average_latency_ms"] == 25.0
    assert result["slowest_request_ms"] == 40.0


def test_empty_metrics_return_zero_values():
    collector = MetricsCollector()

    result = collector.get_metrics("test-service")

    assert result["total_requests"] == 0
    assert result["error_requests"] == 0
    assert result["average_latency_ms"] == 0.0
    assert result["p95_latency_ms"] == 0.0
