
from integrations.online_store_client import fetch_online_inventory
from integrations.erp_client import fetch_erp_inventory
from inventory import compare_inventory


def get_inventory_comparison() -> list[dict]:
    """
    Fetch inventory from both systems and compare it.

    If either source fails, stop and report the failure.
    Never present an incomplete comparison as complete.
    """

    online_inventory = fetch_online_inventory()
    erp_inventory = fetch_erp_inventory()

    return compare_inventory(
        online_store=online_inventory,
        erp_system=erp_inventory,
    )
