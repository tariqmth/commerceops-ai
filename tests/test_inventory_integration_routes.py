
import main
from fastapi.testclient import TestClient


client = TestClient(main.app)


SAMPLE_INVENTORY = [
    {
        "sku": "SKU-101",
        "product_name": "Wireless Mouse",
        "online_quantity": 20,
        "erp_quantity": 15,
        "difference": 5,
        "status": "discrepancy",
    },
    {
        "sku": "SKU-102",
        "product_name": "Mechanical Keyboard",
        "online_quantity": 8,
        "erp_quantity": 8,
        "difference": 0,
        "status": "matched",
    },
    {
        "sku": "SKU-103",
        "product_name": "USB-C Hub",
        "online_quantity": 12,
        "erp_quantity": 10,
        "difference": 2,
        "status": "discrepancy",
    },
]


def test_discrepancies_endpoint_returns_only_discrepancies(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_inventory_comparison",
        lambda: SAMPLE_INVENTORY,
    )

    response = client.get("/inventory/discrepancies")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {item["sku"] for item in data} == {"SKU-101", "SKU-103"}


def test_summary_endpoint_returns_correct_counts(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_inventory_comparison",
        lambda: SAMPLE_INVENTORY,
    )

    response = client.get("/inventory/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_skus": 3,
        "discrepancy_count": 2,
        "matched_count": 1,
    }


def test_discrepancies_endpoint_handles_unavailable_service(monkeypatch):
    def unavailable():
        raise RuntimeError("Internal connection details")

    monkeypatch.setattr(main, "get_inventory_comparison", unavailable)

    response = client.get("/inventory/discrepancies")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Inventory systems are temporarily unavailable."
    )
    assert "Internal connection details" not in response.text


def test_summary_endpoint_handles_invalid_upstream_data(monkeypatch):
    def invalid_data():
        raise ValueError("Internal validation details")

    monkeypatch.setattr(main, "get_inventory_comparison", invalid_data)

    response = client.get("/inventory/summary")

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Inventory systems returned invalid data."
    )
    assert "Internal validation details" not in response.text
