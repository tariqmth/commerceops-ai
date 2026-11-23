
"""Client for retrieving and validating inventory from the ERP service."""

from integrations.online_store_client import (
    fetch_online_inventory,
    validate_inventory_payload,
)


def fetch_erp_inventory(
    base_url: str = "http://127.0.0.1:8002",
) -> dict:
    """Fetch and validate inventory from the mock ERP."""

    # Reuse the same HTTP/validation contract for now.
    # The ERP can later have its own field mapping if needed.
    import httpx

    from integrations.http_utils import get_json_with_retries
    payload = get_json_with_retries(
    f"{base_url.rstrip('/')}/inventory",
    "ERP",
)

    return validate_inventory_payload(payload)

def update_erp_inventory(
    sku: str,
    quantity: int,
    base_url: str = "http://127.0.0.1:8002",
) -> dict:
    """Update inventory in the ERP mock API."""

    import httpx

    from integrations.request_context import request_id_var

    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("SKU cannot be empty")

    if type(quantity) is not int or quantity < 0:
        raise ValueError("Quantity must be a non-negative integer")

    response = httpx.put(
        f"{base_url}/inventory/{sku}",
        json={"quantity": quantity},
        headers={"X-Request-ID": request_id_var.get()},
        timeout=10,
    )

    response.raise_for_status()

    return response.json()