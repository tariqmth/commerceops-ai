
from concurrent.futures import ThreadPoolExecutor

import pytest

from integrations import approval_service


@pytest.fixture(autouse=True)
def clear_approvals():
    """Keep approval data isolated between tests."""

    with approval_service._approval_lock:
        approval_service._APPROVALS.clear()


def disable_audit(monkeypatch):
    """Disable audit writes for tests that don't inspect audit events."""

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )


def test_create_approval_starts_as_pending(monkeypatch):
    audit_events = []

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        lambda event_type, details=None: audit_events.append(
            (event_type, details)
        ),
    )

    approval = approval_service.create_approval(
        action_type="inventory_adjustment",
        description="Correct SKU-101 inventory",
        proposed_changes={
            "sku": "SKU-101",
            "proposed_quantity": 20,
        },
    )

    assert approval["approval_id"]
    assert approval["status"] == "pending"
    assert approval["action_type"] == "inventory_adjustment"
    assert approval["decision"] is None
    assert audit_events[0][0] == "approval_created"


def test_get_approval_returns_existing_approval(monkeypatch):
    disable_audit(monkeypatch)

    created = approval_service.create_approval(
        "refund",
        "Refund customer order",
        {"order_id": "ORDER-101", "amount": 50},
    )

    retrieved = approval_service.get_approval(created["approval_id"])

    assert retrieved["approval_id"] == created["approval_id"]
    assert retrieved["status"] == "pending"


def test_get_approval_returns_none_for_unknown_id():
    assert approval_service.get_approval("unknown-id") is None


def test_approve_pending_inventory_request(monkeypatch):
    audit_events = []

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        lambda event_type, details=None: audit_events.append(
            (event_type, details)
        ),
    )

    approval = approval_service.create_approval(
        "inventory_adjustment",
        "Correct stock quantity",
        {"sku": "SKU-101", "proposed_quantity": 20},
    )

    result = approval_service.decide_approval(
        approval["approval_id"],
        "approved",
        "warehouse_manager",
        "warehouse_manager",
        "Stock count verified",
    )

    assert result["status"] == "approved"
    assert result["decision"]["decided_by"] == "warehouse_manager"
    assert result["decision"]["role"] == "warehouse_manager"
    assert result["decision"]["comment"] == "Stock count verified"

    assert audit_events[-1][0] == "approval_decided"
    assert audit_events[-1][1]["decision"] == "approved"
    assert audit_events[-1][1]["role"] == "warehouse_manager"


def test_reject_pending_order_cancellation(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "order_cancellation",
        "Cancel order ORDER-101",
        {"order_id": "ORDER-101"},
    )

    result = approval_service.decide_approval(
        approval["approval_id"],
        "rejected",
        "operations_manager",
        "operations_manager",
        "Customer requested to keep the order",
    )

    assert result["status"] == "rejected"
    assert result["decision"]["decided_by"] == "operations_manager"
    assert result["decision"]["role"] == "operations_manager"


def test_invalid_action_type_is_rejected():
    with pytest.raises(ValueError, match="Unsupported action type"):
        approval_service.create_approval(
            "delete_database",
            "Delete database",
            {"database": "production"},
        )


def test_empty_description_is_rejected():
    with pytest.raises(ValueError, match="Description cannot be empty"):
        approval_service.create_approval(
            "refund",
            "   ",
            {"order_id": "ORDER-101"},
        )


def test_empty_proposed_changes_are_rejected():
    with pytest.raises(ValueError, match="non-empty dictionary"):
        approval_service.create_approval(
            "refund",
            "Refund order",
            {},
        )


def test_invalid_decision_is_rejected(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101"},
    )

    with pytest.raises(ValueError, match="Decision must be"):
        approval_service.decide_approval(
            approval["approval_id"],
            "maybe",
            "finance_manager",
            "finance_manager",
        )


def test_decided_approval_cannot_be_decided_again(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101"},
    )

    approval_service.decide_approval(
        approval["approval_id"],
        "approved",
        "finance_manager",
        "finance_manager",
    )

    with pytest.raises(ValueError, match="already been decided"):
        approval_service.decide_approval(
            approval["approval_id"],
            "rejected",
            "another_manager",
            "finance_manager",
        )


def test_decision_requires_approver_identity(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101"},
    )

    with pytest.raises(ValueError, match="Decided by cannot be empty"):
        approval_service.decide_approval(
            approval["approval_id"],
            "approved",
            "   ",
            "finance_manager",
        )


def test_decision_requires_valid_role(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101"},
    )

    with pytest.raises(ValueError, match="Role cannot be empty"):
        approval_service.decide_approval(
            approval["approval_id"],
            "approved",
            "manager",
            "   ",
        )


def test_finance_manager_cannot_approve_inventory_adjustment(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "inventory_adjustment",
        "Correct stock",
        {"sku": "SKU-101", "proposed_quantity": 20},
    )

    with pytest.raises(PermissionError):
        approval_service.decide_approval(
            approval["approval_id"],
            "approved",
            "finance_manager",
            "finance_manager",
        )

    stored = approval_service.get_approval(approval["approval_id"])
    assert stored["status"] == "pending"


def test_warehouse_manager_cannot_approve_refund(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101", "amount": 50},
    )

    with pytest.raises(PermissionError):
        approval_service.decide_approval(
            approval["approval_id"],
            "approved",
            "warehouse_manager",
            "warehouse_manager",
        )

    stored = approval_service.get_approval(approval["approval_id"])
    assert stored["status"] == "pending"


def test_unknown_role_cannot_approve_any_action(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101"},
    )

    with pytest.raises(PermissionError):
        approval_service.decide_approval(
            approval["approval_id"],
            "approved",
            "unknown_user",
            "unknown_role",
        )

    stored = approval_service.get_approval(approval["approval_id"])
    assert stored["status"] == "pending"


def test_approval_does_not_modify_proposed_changes(monkeypatch):
    disable_audit(monkeypatch)

    original_changes = {
        "sku": "SKU-101",
        "proposed_quantity": 20,
    }

    approval = approval_service.create_approval(
        "inventory_adjustment",
        "Correct stock",
        original_changes,
    )

    original_changes["proposed_quantity"] = 999

    stored = approval_service.get_approval(approval["approval_id"])

    assert stored["proposed_changes"]["proposed_quantity"] == 20


def test_nested_approval_data_cannot_be_modified_externally(monkeypatch):
    disable_audit(monkeypatch)

    original_changes = {
        "sku": "SKU-101",
        "inventory": {
            "current": 15,
            "proposed": 20,
        },
    }

    approval = approval_service.create_approval(
        "inventory_adjustment",
        "Correct stock",
        original_changes,
    )

    # Modify the original input.
    original_changes["inventory"]["proposed"] = 999

    # Modify the returned approval.
    approval["proposed_changes"]["inventory"]["proposed"] = 888

    stored = approval_service.get_approval(approval["approval_id"])

    assert stored["proposed_changes"]["inventory"]["proposed"] == 20

    # Modify retrieved data and check storage again.
    stored["proposed_changes"]["inventory"]["proposed"] = 777

    final_result = approval_service.get_approval(approval["approval_id"])

    assert final_result["proposed_changes"]["inventory"]["proposed"] == 20


def test_create_approval_rolls_back_when_audit_fails(monkeypatch):
    def failing_audit(*args, **kwargs):
        raise OSError("Audit storage unavailable")

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        failing_audit,
    )

    with pytest.raises(OSError, match="Audit storage unavailable"):
        approval_service.create_approval(
            "inventory_adjustment",
            "Correct SKU-101 stock",
            {
                "sku": "SKU-101",
                "proposed_quantity": 20,
            },
        )

    with approval_service._approval_lock:
        assert len(approval_service._APPROVALS) == 0


def test_decision_is_not_saved_when_audit_fails(monkeypatch):
    """A failed audit write must not leave an unaudited decision."""

    def failing_audit(*args, **kwargs):
        raise OSError("Audit storage unavailable")

    # Allow creation, but fail when the decision is recorded.
    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    approval = approval_service.create_approval(
        "refund",
        "Refund order",
        {"order_id": "ORDER-101"},
    )

    monkeypatch.setattr(
        approval_service,
        "record_audit_event",
        failing_audit,
    )

    with pytest.raises(OSError, match="Audit storage unavailable"):
        approval_service.decide_approval(
            approval["approval_id"],
            "approved",
            "finance_manager",
            "finance_manager",
        )

    stored = approval_service.get_approval(approval["approval_id"])

    # This assertion requires approval_service.py to write the audit
    # event before changing the approval status.
    assert stored["status"] == "pending"
    assert stored["decision"] is None


def test_only_one_concurrent_approval_decision_succeeds(monkeypatch):
    disable_audit(monkeypatch)

    approval = approval_service.create_approval(
        "inventory_adjustment",
        "Correct SKU-101 stock",
        {
            "sku": "SKU-101",
            "proposed_quantity": 20,
        },
    )

    def make_decision(decision):
        try:
            approval_service.decide_approval(
                approval["approval_id"],
                decision,
                f"warehouse_manager_{decision}",
                "warehouse_manager",
            )
            return "success"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                make_decision,
                ["approved", "rejected"],
            )
        )

    assert results.count("success") == 1
    assert results.count("rejected") == 1

    final_approval = approval_service.get_approval(
        approval["approval_id"]
    )

    assert final_approval["status"] in {"approved", "rejected"}
