"""Tests for retry behavior when fetching JSON from integrations."""

import httpx
import pytest

from integrations.http_utils import get_json_with_retries


def test_retries_transient_server_error_then_succeeds(monkeypatch):
    calls = 0

    def mock_get(url, timeout):
        nonlocal calls
        calls += 1

        request = httpx.Request("GET", url)

        if calls == 1:
            return httpx.Response(503, request=request)

        return httpx.Response(
            200,
            json={"inventory": {}},
            request=request,
        )

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr("integrations.http_utils.time.sleep", lambda _: None)

    result = get_json_with_retries("http://test/inventory", "Test service")

    assert result == {"inventory": {}}
    assert calls == 2


def test_stops_after_max_attempts_for_transient_failure(monkeypatch):
    calls = 0

    def mock_get(url, timeout):
        nonlocal calls
        calls += 1
        request = httpx.Request("GET", url)
        return httpx.Response(503, request=request)

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr("integrations.http_utils.time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="after 3 attempts"):
        get_json_with_retries("http://test/inventory", "Test service")

    assert calls == 3


def test_does_not_retry_client_error(monkeypatch):
    calls = 0

    def mock_get(url, timeout):
        nonlocal calls
        calls += 1
        request = httpx.Request("GET", url)
        return httpx.Response(404, request=request)

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr("integrations.http_utils.time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="HTTP 404"):
        get_json_with_retries("http://test/inventory", "Test service")

    assert calls == 1


def test_does_not_retry_invalid_json(monkeypatch):
    calls = 0

    def mock_get(url, timeout):
        nonlocal calls
        calls += 1
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            content=b"not valid json",
            request=request,
        )

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr("integrations.http_utils.time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="invalid JSON"):
        get_json_with_retries("http://test/inventory", "Test service")

    assert calls == 1

def test_retries_timeout_then_succeeds(monkeypatch):
    calls = 0

    def mock_get(url, timeout):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise httpx.TimeoutException("Request timed out")

        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"inventory": {}},
            request=request,
        )

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr("integrations.http_utils.time.sleep", lambda _: None)

    result = get_json_with_retries("http://test/inventory", "Test service")

    assert result == {"inventory": {}}
    assert calls == 2

def test_stops_after_max_attempts_for_connection_error(monkeypatch):
    calls = 0

    def mock_get(url, timeout):
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr("integrations.http_utils.time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="after 3 attempts"):
        get_json_with_retries("http://test/inventory", "Test service")

    assert calls == 3