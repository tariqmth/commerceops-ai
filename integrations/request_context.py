"""Context-local request IDs used to correlate logs and downstream calls."""

import contextvars
import logging

request_id_var = contextvars.ContextVar(
    "request_id",
    default="-",
)


class RequestIdFilter(logging.Filter):
    """Add the current request ID to every log record."""

    def filter(self, record):
        record.request_id = request_id_var.get()
        return True