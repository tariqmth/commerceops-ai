
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