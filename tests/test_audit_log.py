
import json

from integrations import audit_log
from integrations.request_context import request_id_var


def test_audit_event_is_written(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.jsonl"

    monkeypatch.setattr(
        audit_log,
        "AUDIT_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        audit_log,
        "AUDIT_FILE",
        audit_file,
    )

    token = request_id_var.set("test-request-123")

    try:
        audit_log.record_audit_event(
            "ai_request_started",
            {"question_type": "inventory"},
        )
    finally:
        request_id_var.reset(token)

    events = audit_file.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(events) == 1

    event = json.loads(events[0])

    assert event["request_id"] == "test-request-123"
    assert event["event_type"] == "ai_request_started"
    assert event["details"]["question_type"] == "inventory"


def test_audit_events_are_appended(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.jsonl"

    monkeypatch.setattr(
        audit_log,
        "AUDIT_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        audit_log,
        "AUDIT_FILE",
        audit_file,
    )

    audit_log.record_audit_event("first_event")
    audit_log.record_audit_event("second_event")

    events = audit_file.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(events) == 2

    assert json.loads(events[0])["event_type"] == "first_event"
    assert json.loads(events[1])["event_type"] == "second_event"

def test_audit_write_failure_raises_error(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.jsonl"

    monkeypatch.setattr(
        audit_log,
        "AUDIT_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        audit_log,
        "AUDIT_FILE",
        audit_file,
    )

    # Make the audit file path a directory.
    # Opening a directory as a file should raise an OSError.
    audit_file.mkdir()

    import pytest

    with pytest.raises(OSError):
        audit_log.record_audit_event(
            "ai_request_started",
            {"question_type": "inventory"},
        )