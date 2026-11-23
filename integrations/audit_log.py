
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from integrations.request_context import request_id_var

logger = logging.getLogger(__name__)

AUDIT_DIRECTORY = Path("audit_logs")
AUDIT_FILE = AUDIT_DIRECTORY / "audit.jsonl"

_audit_lock = Lock()


def record_audit_event(
    event_type: str,
    details: dict | None = None,
) -> None:
    """
    Append one structured audit event to the JSONL audit file.
    """

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id_var.get(),
        "event_type": event_type,
        "service": "commerceops-ai",
        "details": details or {},
    }

    try:
        AUDIT_DIRECTORY.mkdir(parents=True, exist_ok=True)

        with _audit_lock:
            with AUDIT_FILE.open("a", encoding="utf-8") as file:
                file.write(json.dumps(event, default=str) + "\n")

    except OSError:
        logger.exception(
            "Failed to write audit event: %s",
            event_type,
        )
        raise
