
from inventory import compare_inventory


def get_inventory_discrepancies() -> dict:
    """
    Read-only tool that compares online store inventory
    against ERP inventory.
    """
    results = compare_inventory()

    discrepancies = [
        item
        for item in results
        if item["status"] != "matched"
    ]

    return {
        "total_skus": len(results),
        "discrepancy_count": len(discrepancies),
        "discrepancies": discrepancies,
    }
