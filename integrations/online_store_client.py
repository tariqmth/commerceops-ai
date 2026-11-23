
"""Client for retrieving and validating online-store inventory."""

import httpx
from integrations.http_utils import get_json_with_retries
from integrations.request_context import request_id_var

def fetch_online_inventory(
    base_url: str = "http://127.0.0.1:8001",) -> dict:
    """Fetch and validate inventory from the mock online store."""

    payload = get_json_with_retries(
        f"{base_url.rstrip('/')}/inventory",
        "Online store",
    )

    return validate_inventory_payload(payload)


def validate_inventory_payload(payload: dict) -> dict:
    """Validate the response and return canonical inventory data."""

    if not isinstance(payload, dict):
        raise ValueError("Inventory response must be an object")

    inventory = payload.get("inventory")

    if not isinstance(inventory, dict):
        raise ValueError("Inventory response is missing inventory data")

    for sku, record in inventory.items():
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError("Inventory contains an invalid SKU")

        if not isinstance(record, dict):
            raise ValueError(f"Invalid inventory record for {sku}")

        name = record.get("product_name")
        quantity = record.get("quantity")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid product name for {sku}")

        # bool is a subclass of int in Python, so reject it explicitly.
        if type(quantity) is not int or quantity < 0:
            raise ValueError(f"Invalid quantity for {sku}")

    return inventory


def update_online_inventory(
    sku: str,
    quantity: int,
    base_url: str = "http://127.0.0.1:8001",
) -> dict:
    """Update inventory in the mock online store."""

    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("SKU cannot be empty")

    if type(quantity) is not int or quantity < 0:
        raise ValueError("Quantity must be a non-negative integer")

    response = httpx.put(
        f"{base_url.rstrip('/')}/inventory/{sku}",
        json={"quantity": quantity},
        headers={
            "X-Request-ID": request_id_var.get(),
        },
        timeout=10.0,
    )

    response.raise_for_status()

    return response.json()
