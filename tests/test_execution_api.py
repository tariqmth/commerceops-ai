
import pytest
from fastapi.testclient import TestClient

import main
from integrations import approval_service, execution_service


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_execution_records():
    """Keep execution records isolated between tests."""

    with execution_service._execution_lock:
        execution_service._EXECUTIONS.clear()


@pytest.fixture
def approved_adjustment(monkeypatch):
    """Provide an approved inventory adjustment."""

    approval = {
        "approval_id": "approval-api-test-001",
        "status": "approved",
        "action_type": "inventory_adjustment",
        "proposed_changes": {
            "sku": "SKU-101",
            "target_quantity": 18,
            "physical_count": 18,
            "count_reference": "COUNT-2026-001",
            "reason": "Physical stock reconciliation",
            "expected_online_quantity": 20,
            "expected_erp_quantity": 15,
        },
    }

    monkeypatch.setattr(
        approval_service,
        "get_approval",
        lambda approval_id: (
            approval
            if approval_id == approval["approval_id"]
            else None
        ),
    )

    return approval


def test_execute_endpoint_success(
    client,
    monkeypatch,
    approved_adjustment,
):
    """Successful execution returns HTTP 200."""

    result = {
        "approval_id": "approval-api-test-001",
        "status": "completed",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store", "erp"],
        "verification_passed": True,
    }

    monkeypatch.setattr(
        execution_service,
        "execute_approved_inventory_adjustment",
        lambda approval_id: result,
    )

    response = client.post(
        "/approvals/approval-api-test-001/execute"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["verification_passed"] is True


def test_execute_endpoint_rejects_pending_approval(
    client,
    monkeypatch,
    approved_adjustment,
):
    """Pending approval cannot be executed."""

    def reject_execution(approval_id):
        raise ValueError(
            "Approval must be approved before execution"
        )

    monkeypatch.setattr(
        execution_service,
        "execute_approved_inventory_adjustment",
        reject_execution,
    )

    response = client.post(
        "/approvals/approval-api-test-001/execute"
    )

    assert response.status_code == 400
    assert "must be approved" in response.json()["detail"]


def test_execute_endpoint_returns_404_for_unknown_approval(
    client,
    monkeypatch,
):
    """Unknown approval returns HTTP 404."""

    def reject_execution(approval_id):
        raise ValueError("Approval not found")

    monkeypatch.setattr(
        execution_service,
        "execute_approved_inventory_adjustment",
        reject_execution,
    )

    response = client.post(
        "/approvals/unknown-approval/execute"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Approval not found"


def test_execute_endpoint_rejects_duplicate_execution(
    client,
    monkeypatch,
    approved_adjustment,
):
    """Duplicate execution returns HTTP 400."""

    def reject_execution(approval_id):
        raise ValueError(
            "An execution attempt already exists for this approval"
        )

    monkeypatch.setattr(
        execution_service,
        "execute_approved_inventory_adjustment",
        reject_execution,
    )

    response = client.post(
        "/approvals/approval-api-test-001/execute"
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_execute_endpoint_returns_conflict_on_execution_failure(
    client,
    monkeypatch,
    approved_adjustment,
):
    """Execution failure returns HTTP 409 and its execution record."""

    execution_record = {
        "approval_id": "approval-api-test-001",
        "status": "partial_failure",
        "updated_services": ["online_store"],
        "verification_passed": False,
        "failure_type": "RuntimeError",
    }

    def fail_execution(approval_id):
        raise RuntimeError("Inventory adjustment execution failed")

    monkeypatch.setattr(
        execution_service,
        "execute_approved_inventory_adjustment",
        fail_execution,
    )

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: execution_record,
    )

    response = client.post(
        "/approvals/approval-api-test-001/execute"
    )

    assert response.status_code == 409

    body = response.json()

    assert "did not complete" in body["detail"]["message"]
    assert body["detail"]["execution"]["status"] == "partial_failure"


def test_get_execution_endpoint_returns_execution_record(
    client,
    monkeypatch,
):
    """Existing execution record can be retrieved."""

    execution_record = {
        "approval_id": "approval-api-test-001",
        "status": "completed",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store", "erp"],
        "verification_passed": True,
    }

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: execution_record,
    )

    response = client.get(
        "/approvals/approval-api-test-001/execution"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["target_quantity"] == 18


def test_get_execution_endpoint_returns_404_when_missing(
    client,
    monkeypatch,
):
    """Missing execution record returns HTTP 404."""

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: None,
    )

    response = client.get(
        "/approvals/unknown-approval/execution"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Execution record not found."


def test_execute_endpoint_returns_200_when_execution_is_reconciled(
    client,
    monkeypatch,
    approved_adjustment,
):
    """Lost update response with verified state returns HTTP 200."""

    result = {
        "approval_id": "approval-api-test-001",
        "status": "reconciled",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store", "erp"],
        "verification_passed": True,
        "observed_quantities": {
            "online_store": 18,
            "erp": 18,
        },
        "failure_type": "TimeoutError",
        "failure_message": "ERP response lost after remote update",
    }

    monkeypatch.setattr(
        execution_service,
        "execute_approved_inventory_adjustment",
        lambda approval_id: result,
    )

    response = client.post(
        "/approvals/approval-api-test-001/execute"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "reconciled"
    assert body["verification_passed"] is True
    assert body["observed_quantities"]["online_store"] == 18
    assert body["observed_quantities"]["erp"] == 18
