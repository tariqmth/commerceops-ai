
"""Tests for integration health-check responses and aggregation."""

import httpx

from integrations.health_service import (
    check_service_health,
    get_integrations_health,
)


def test_service_health_returns_healthy(monkeypatch):
    def mock_get(url, timeout):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"status": "ok"},
            request=request,
        )

    monkeypatch.setattr(httpx, "get", mock_get)

    result = check_service_health(
        "http://test",
        "test-service",
    )

    assert result["service"] == "test-service"
    assert result["status"] == "healthy"


def test_service_health_returns_unhealthy_for_http_error(monkeypatch):
    def mock_get(url, timeout):
        request = httpx.Request("GET", url)
        return httpx.Response(503, request=request)

    monkeypatch.setattr(httpx, "get", mock_get)

    result = check_service_health(
        "http://test",
        "test-service",
    )

    assert result["status"] == "unhealthy"
    assert result["message"] == "Service is unavailable"


def test_service_health_returns_unhealthy_for_timeout(monkeypatch):
    def mock_get(url, timeout):
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr(httpx, "get", mock_get)

    result = check_service_health(
        "http://test",
        "test-service",
    )

    assert result["status"] == "unhealthy"


def test_integrations_health_returns_healthy_when_both_work(monkeypatch):
    def mock_check(base_url, service_name):
        return {
            "service": service_name,
            "status": "healthy",
        }

    monkeypatch.setattr(
        "integrations.health_service.check_service_health",
        mock_check,
    )

    result = get_integrations_health()

    assert result["status"] == "healthy"
    assert len(result["services"]) == 2
    assert all(
        service["status"] == "healthy"
        for service in result["services"]
    )


def test_integrations_health_returns_degraded_when_one_fails(monkeypatch):
    def mock_check(base_url, service_name):
        status = (
            "healthy"
            if service_name == "online-store"
            else "unhealthy"
        )

        return {
            "service": service_name,
            "status": status,
        }

    monkeypatch.setattr(
        "integrations.health_service.check_service_health",
        mock_check,
    )

    result = get_integrations_health()

    assert result["status"] == "degraded"
    assert result["services"][0]["status"] == "healthy"
    assert result["services"][1]["status"] == "unhealthy"
