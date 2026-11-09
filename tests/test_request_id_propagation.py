
"""Tests for request-ID propagation through outbound integration calls."""

import httpx

from integrations.http_utils import get_json_with_retries
from integrations.request_context import request_id_var


def test_http_client_propagates_request_id(monkeypatch):
    captured = {}

    def mock_get(url, timeout, headers=None):
        captured["url"] = url
        captured["headers"] = headers

        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"status": "ok"},
            request=request,
        )

    monkeypatch.setattr(httpx, "get", mock_get)

    token = request_id_var.set("test-request-123")

    try:
        result = get_json_with_retries(
            "http://test-service/inventory",
            "Test service",
        )
    finally:
        request_id_var.reset(token)

    assert result == {"status": "ok"}
    assert captured["headers"]["X-Request-ID"] == "test-request-123"


def test_http_client_works_without_request_id(monkeypatch):
    captured = {}

    def mock_get(url, timeout, headers=None):
        captured["headers"] = headers

        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"status": "ok"},
            request=request,
        )

    monkeypatch.setattr(httpx, "get", mock_get)

    result = get_json_with_retries(
        "http://test-service/inventory",
        "Test service",
    )

    assert result == {"status": "ok"}
    assert captured["headers"] is None
