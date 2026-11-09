"""Tests for request-ID response headers and per-request uniqueness."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_response_contains_request_id():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_each_request_gets_a_unique_request_id():
    first = client.get("/health")
    second = client.get("/health")

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]

    assert first_id != second_id