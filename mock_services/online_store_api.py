
"""Mock online-store API providing health status and inventory operations."""

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from integrations.request_context import request_id_var


app = FastAPI(title="Mock Online Store API")

logger = logging.getLogger("online_store_api")


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


class InventoryUpdateRequest(BaseModel):
    quantity: int = Field(ge=0, strict=True)


@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    """Propagate request IDs across service calls."""

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


@app.get("/health")
def health():
    return {"status": "ok", "service": "online-store"}


@app.get("/inventory")
def get_inventory():
    return {"inventory": ONLINE_INVENTORY}


@app.put("/inventory/{sku}")
def update_inventory(sku: str, request: InventoryUpdateRequest):
    """Update the quantity of an existing SKU in the mock online store."""

    record = ONLINE_INVENTORY.get(sku)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory SKU not found.",
        )

    previous_quantity = record["quantity"]

    record["quantity"] = request.quantity

    logger.info(
        "Inventory updated sku=%s previous_quantity=%s new_quantity=%s",
        sku,
        previous_quantity,
        request.quantity,
    )

    return {
        "service": "online-store",
        "sku": sku,
        "previous_quantity": previous_quantity,
        "new_quantity": request.quantity,
        "status": "updated",
    }
