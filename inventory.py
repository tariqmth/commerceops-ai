
ONLINE_STORE = {
    "SKU-101": {"product_name": "Wireless Mouse", "quantity": 20},
    "SKU-102": {"product_name": "Mechanical Keyboard", "quantity": 8},
    "SKU-103": {"product_name": "USB-C Hub", "quantity": 12},
}

ERP_SYSTEM = {
    "SKU-101": {"product_name": "Wireless Mouse", "quantity": 15},
    "SKU-102": {"product_name": "Mechanical Keyboard", "quantity": 8},
    "SKU-103": {"product_name": "USB-C Hub", "quantity": 10},
}


def compare_inventory(online_store=None, erp_system=None):
    online_store = ONLINE_STORE if online_store is None else online_store
    erp_system = ERP_SYSTEM if erp_system is None else erp_system

    validate_inventory(online_store)
    validate_inventory(erp_system)
    
    results = []
    all_skus = sorted(set(online_store) | set(erp_system))

    for sku in all_skus:
        online = online_store.get(sku)
        erp = erp_system.get(sku)

        if online is None or erp is None:
            results.append({
                "sku": sku,
                "product_name": (
                    online["product_name"] if online else erp["product_name"]
                ),
                "online_quantity": online["quantity"] if online else None,
                "erp_quantity": erp["quantity"] if erp else None,
                "difference": None,
                "status": "missing_from_system",
            })
            continue

        difference = online["quantity"] - erp["quantity"]

        results.append({
            "sku": sku,
            "product_name": online["product_name"],
            "online_quantity": online["quantity"],
            "erp_quantity": erp["quantity"],
            "difference": difference,
            "status": "matched" if difference == 0 else "discrepancy",
        })

    return results


def validate_inventory(inventory):
    """Validate inventory records before comparison."""

    for sku, product in inventory.items():
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError("SKU must be a non-empty string")

        if not isinstance(product, dict):
            raise ValueError(f"Invalid inventory record for {sku}")

        quantity = product.get("quantity")

        # bool is a subclass of int in Python, so reject it explicitly.
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError(f"Quantity for {sku} must be an integer")

        if quantity < 0:
            raise ValueError(f"Quantity for {sku} cannot be negative")

        if not isinstance(product.get("product_name"), str):
            raise ValueError(f"Product name for {sku} must be a string")
