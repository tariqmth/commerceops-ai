
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_compare_inventory_returns_discrepancy():
    response = client.post(
        "/inventory/compare",
        json={
            "online_store": {
                "SKU-101": {
                    "product_name": "Wireless Mouse",
                    "quantity": 20,
                }
            },
            "erp_system": {
                "SKU-101": {
                    "product_name": "Wireless Mouse",
                    "quantity": 15,
                }
            },
        },
    )

    assert response.status_code == 200

    result = response.json()[0]
    assert result["sku"] == "SKU-101"
    assert result["difference"] == 5
    assert result["status"] == "discrepancy"


def test_compare_inventory_rejects_negative_quantity():
    response = client.post(
        "/inventory/compare",
        json={
            "online_store": {
                "SKU-101": {
                    "product_name": "Wireless Mouse",
                    "quantity": -1,
                }
            },
            "erp_system": {},
        },
    )

    assert response.status_code == 422
