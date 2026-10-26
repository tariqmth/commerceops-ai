
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

    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/inventory",
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()

    except httpx.TimeoutException as exc:
        raise RuntimeError("ERP service timed out") from exc

    except httpx.HTTPError as exc:
        raise RuntimeError("ERP service request failed") from exc

    except ValueError as exc:
        raise RuntimeError("ERP returned invalid JSON") from exc

    return validate_inventory_payload(payload)
