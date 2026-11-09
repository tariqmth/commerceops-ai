
"""Mock online-store API providing health status and sample inventory data."""

from fastapi import FastAPI
import logging
import uuid

from fastapi import FastAPI, Request
from integrations.request_context import request_id_var

app = FastAPI(title="Mock Online Store API")

logger = logging.getLogger("online_store_api")


@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    # Reuse the ID from the main application, or generate one for direct calls.
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    token = request_id_var.set(request_id)

    try:
        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "Request completed request_id=%s method=%s path=%s status_code=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
        )

        return response

    except Exception:
        logger.exception(
            "Request failed request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        raise

    finally:
        request_id_var.reset(token)

ONLINE_INVENTORY = {
    "SKU-101": {
        "product_name": "Wireless Mouse",
        "quantity": 20,
    },
    "SKU-102": {
        "product_name": "Mechanical Keyboard",
        "quantity": 8,
    },
    "SKU-103": {
        "product_name": "USB-C Hub",
        "quantity": 12,
    },
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "online-store"}


@app.get("/inventory")
def get_inventory():
    return {"inventory": ONLINE_INVENTORY}
