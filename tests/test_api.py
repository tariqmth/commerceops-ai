
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_inventory_summary_endpoint(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_inventory_comparison",
        main.compare_inventory,
    )

    response = client.get("/inventory/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_skus": 3,
        "discrepancy_count": 2,
        "matched_count": 1,
    }
