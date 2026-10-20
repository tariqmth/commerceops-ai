
from inventory import compare_inventory


def test_inventory_comparison_detects_discrepancies():
    results = compare_inventory()
    by_sku = {item["sku"]: item for item in results}

    assert by_sku["SKU-101"]["difference"] == 5
    assert by_sku["SKU-101"]["status"] == "discrepancy"

    assert by_sku["SKU-102"]["difference"] == 0
    assert by_sku["SKU-102"]["status"] == "matched"

    assert by_sku["SKU-103"]["difference"] == 2
    assert by_sku["SKU-103"]["status"] == "discrepancy"


def test_missing_sku_is_reported():
    online = {
        "SKU-104": {"product_name": "Test Product", "quantity": 4}
    }

    results = compare_inventory(online_store=online, erp_system={})

    assert len(results) == 1
    assert results[0]["sku"] == "SKU-104"
    assert results[0]["status"] == "missing_from_system"
    assert results[0]["erp_quantity"] is None
    assert results[0]["difference"] is None


def test_empty_inventories_return_no_results():
    assert compare_inventory(online_store={}, erp_system={}) == []
