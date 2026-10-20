
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_inventory_summary_endpoint():
    response = client.get("/inventory/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_skus": 3,
        "matched": 1,
        "discrepancies": 2,
        "missing_from_system": 0,
    }
