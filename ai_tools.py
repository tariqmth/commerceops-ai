
from integrations.inventory_service import get_inventory_comparison


def get_inventory_discrepancies() -> dict:
    """
    Read-only tool that compares online-store inventory
    against ERP inventory using their HTTP APIs.
    """

    results = get_inventory_comparison()

    discrepancies = [
        item for item in results
        if item["status"] != "matched"
    ]

    return {
        "total_skus": len(results),
        "discrepancy_count": len(discrepancies),
        "discrepancies": discrepancies,
    }
