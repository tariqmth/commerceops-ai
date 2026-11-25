
import pytest
from fastapi.testclient import TestClient

import main
from integrations import execution_service


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def partial_execution():
    """Provide a partially completed inventory execution."""

    return {
        "approval_id": "approval-recovery-test-001",
        "status": "partial_failure",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store"],
        "verification_passed": False,
        "observed_quantities": {
            "online_store": 18,
            "erp": 15,
        },
    }


def test_recovery_endpoint_success(
    client,
    monkeypatch,
    partial_execution,
):
    """Successful recovery returns HTTP 200."""

    recovered_execution = {
        **partial_execution,
        "status": "recovered",
        "updated_services": ["online_store", "erp"],
        "verification_passed": True,
        "observed_quantities": {
            "online_store": 18,
            "erp": 18,
        },
    }

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: partial_execution,
    )

    monkeypatch.setattr(
        execution_service,
        "recover_partial_inventory_execution",
        lambda approval_id: recovered_execution,
    )

    response = client.post(
        "/approvals/approval-recovery-test-001/recover"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "recovered"
    assert body["verification_passed"] is True
    assert body["observed_quantities"]["online_store"] == 18
    assert body["observed_quantities"]["erp"] == 18


def test_recovery_endpoint_returns_404_when_execution_missing(
    client,
    monkeypatch,
):
    """Missing execution record returns HTTP 404."""

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: None,
    )

    response = client.post(
        "/approvals/unknown-approval/recover"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Execution record not found."


def test_recovery_endpoint_returns_400_for_invalid_request(
    client,
    monkeypatch,
    partial_execution,
):
    """Invalid recovery request returns HTTP 400."""

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: partial_execution,
    )

    def reject_recovery(approval_id):
        raise ValueError(
            "Execution is not eligible for recovery"
        )

    monkeypatch.setattr(
        execution_service,
        "recover_partial_inventory_execution",
        reject_recovery,
    )

    response = client.post(
        "/approvals/approval-recovery-test-001/recover"
    )

    assert response.status_code == 400
    assert "not eligible" in response.json()["detail"]


def test_recovery_endpoint_returns_409_on_recovery_failure(
    client,
    monkeypatch,
    partial_execution,
):
    """Recovery failure returns HTTP 409 and execution details."""

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: partial_execution,
    )

    def fail_recovery(approval_id):
        raise RuntimeError("ERP recovery failed")

    monkeypatch.setattr(
        execution_service,
        "recover_partial_inventory_execution",
        fail_recovery,
    )

    response = client.post(
        "/approvals/approval-recovery-test-001/recover"
    )

    assert response.status_code == 409

    body = response.json()

    assert "did not complete" in body["detail"]["message"]
    assert (
        body["detail"]["execution"]["status"]
        == "partial_failure"
    )


def test_recovery_endpoint_returns_503_on_audit_failure(
    client,
    monkeypatch,
    partial_execution,
):
    """Audit storage failure returns HTTP 503."""

    monkeypatch.setattr(
        execution_service,
        "get_execution",
        lambda approval_id: partial_execution,
    )

    def fail_recovery(approval_id):
        raise OSError("Audit storage unavailable")

    monkeypatch.setattr(
        execution_service,
        "recover_partial_inventory_execution",
        fail_recovery,
    )

    response = client.post(
        "/approvals/approval-recovery-test-001/recover"
    )

    assert response.status_code == 503
    assert "audit storage is unavailable" in (
        response.json()["detail"]
    )
