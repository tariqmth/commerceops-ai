
import json
import logging

from integrations.logging_config import JsonFormatter
from integrations.request_context import request_id_var


def test_json_formatter_includes_request_context():
    token = request_id_var.set("test-request-123")

    try:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Inventory request completed",
            args=(),
            exc_info=None,
        )

        formatter = JsonFormatter("test-service")
        result = formatter.format(record)
        data = json.loads(result)

    finally:
        request_id_var.reset(token)

    assert data["level"] == "INFO"
    assert data["service"] == "test-service"
    assert data["request_id"] == "test-request-123"
    assert data["message"] == "Inventory request completed"


def test_json_formatter_includes_structured_fields():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Request completed",
        args=(),
        exc_info=None,
    )

    record.method = "GET"
    record.path = "/inventory"
    record.status_code = 200

    formatter = JsonFormatter("online-store")
    data = json.loads(formatter.format(record))

    assert data["method"] == "GET"
    assert data["path"] == "/inventory"
    assert data["status_code"] == 200

def test_json_formatter_includes_duration():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Request completed",
        args=(),
        exc_info=None,
    )

    record.duration_ms = 42.65

    formatter = JsonFormatter("test-service")
    data = json.loads(formatter.format(record))

    assert data["duration_ms"] == 42.65