
import httpx


def fetch_online_inventory(
    base_url: str = "http://127.0.0.1:8001",
) -> dict:
    """Fetch and validate inventory from the mock online store."""

    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/inventory",
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()

    except httpx.TimeoutException as exc:
        raise RuntimeError(
            "Online store service timed out"
        ) from exc

    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Online store service request failed"
        ) from exc

    except ValueError as exc:
        raise RuntimeError(
            "Online store returned invalid JSON"
        ) from exc

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
