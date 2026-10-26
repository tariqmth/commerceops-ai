
import pytest

from ai_tools import get_inventory_discrepancies


def test_inventory_tool_stops_when_online_store_fails(monkeypatch):
    def fail_online_store():
        raise RuntimeError("Online store service request failed")

    def unexpected_erp_call():
        pytest.fail("ERP should not be called after the online store fails.")

    monkeypatch.setattr(
        "integrations.inventory_service.fetch_online_inventory",
        fail_online_store,
    )
    monkeypatch.setattr(
        "integrations.inventory_service.fetch_erp_inventory",
        unexpected_erp_call,
    )

    with pytest.raises(RuntimeError, match="Online store service request failed"):
        get_inventory_discrepancies()


def test_inventory_tool_stops_when_erp_fails(monkeypatch):
    def online_store_inventory():
        return {
            "SKU-101": {
                "product_name": "Wireless Mouse",
                "quantity": 20,
            }
        }

    def fail_erp():
        raise RuntimeError("ERP service request failed")

    monkeypatch.setattr(
        "integrations.inventory_service.fetch_online_inventory",
        online_store_inventory,
    )
    monkeypatch.setattr(
        "integrations.inventory_service.fetch_erp_inventory",
        fail_erp,
    )

    with pytest.raises(RuntimeError, match="ERP service request failed"):
        get_inventory_discrepancies()
