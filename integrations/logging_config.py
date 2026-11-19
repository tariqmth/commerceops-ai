
import json
import logging
from datetime import datetime, timezone

from integrations.request_context import request_id_var


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "request_id": getattr(
                record,
                "request_id",
                request_id_var.get(),
            ),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured fields when supplied by the caller.
        for field in ("method", "path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def configure_logging(service_name: str):
    """Configure consistent JSON logging for a service."""

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid installing duplicate handlers if configuration is repeated.
    for handler in root_logger.handlers:
        if getattr(handler, "_commerceops_json_handler", False):
            return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service_name))
    handler._commerceops_json_handler = True

    root_logger.addHandler(handler)
