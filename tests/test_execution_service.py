
import pytest

from integrations import execution_service


@pytest.fixture(autouse=True)
def clear_executions():
    """Keep execution records isolated between tests."""

    with execution_service._execution_lock:
        execution_service._EXECUTIONS.clear()


@pytest.fixture
def approved_adjustment(monkeypatch):
    """Provide an approved inventory adjustment."""

    approval = {
        "approval_id": "approval-test-001",
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
        execution_service.approval_service,
        "get_approval",
        lambda approval_id: approval if approval_id == approval["approval_id"] else None,
    )

    return approval


def test_successful_inventory_execution(
    monkeypatch,
    approved_adjustment,
):
    """Both systems update and verification succeeds."""

    inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 20,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 15,
        }
    }

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def update_online(sku, quantity):
        inventory[sku]["quantity"] = quantity

        return {
            "sku": sku,
            "new_quantity": quantity,
            "status": "updated",
        }

    def update_erp(sku, quantity):
        erp_inventory[sku]["quantity"] = quantity

        return {
            "sku": sku,
            "new_quantity": quantity,
            "status": "updated",
        }

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        update_online,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        update_erp,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    result = execution_service.execute_approved_inventory_adjustment(
        "approval-test-001"
    )

    assert result["status"] == "completed"
    assert result["updated_services"] == ["online_store", "erp"]

    assert inventory["SKU-101"]["quantity"] == 18
    assert erp_inventory["SKU-101"]["quantity"] == 18


def test_pending_approval_cannot_execute(
    monkeypatch,
    approved_adjustment,
):
    approved_adjustment["status"] = "pending"

    with pytest.raises(ValueError, match="must be approved"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )


def test_rejected_approval_cannot_execute(
    monkeypatch,
    approved_adjustment,
):
    approved_adjustment["status"] = "rejected"

    with pytest.raises(ValueError, match="must be approved"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )


def test_non_inventory_action_cannot_execute(
    monkeypatch,
    approved_adjustment,
):
    approved_adjustment["action_type"] = "refund"

    with pytest.raises(ValueError, match="Only inventory adjustments"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )


def test_unknown_approval_is_rejected():
    with pytest.raises(ValueError, match="Approval not found"):
        execution_service.execute_approved_inventory_adjustment(
            "unknown-approval"
        )


def test_changed_online_inventory_blocks_execution(
    monkeypatch,
    approved_adjustment,
):
    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: {
            "SKU-101": {
                "product_name": "Wireless Mouse",
                "quantity": 25,
            }
        },
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: {
            "SKU-101": {
                "product_name": "Wireless Mouse",
                "quantity": 15,
            }
        },
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="execution failed"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    execution = execution_service.get_execution("approval-test-001")

    assert execution["status"] == "failed"
    assert execution["updated_services"] == []


def test_duplicate_execution_is_rejected(
    monkeypatch,
    approved_adjustment,
):
    inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 20,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 15,
        }
    }

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def update_inventory(sku, quantity):
        inventory[sku]["quantity"] = quantity
        erp_inventory[sku]["quantity"] = quantity

        return {
            "sku": sku,
            "new_quantity": quantity,
            "status": "updated",
        }

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        update_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        update_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    execution_service.execute_approved_inventory_adjustment(
        "approval-test-001"
    )

    with pytest.raises(ValueError, match="already exists"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )


def test_erp_failure_records_partial_failure(
    monkeypatch,
    approved_adjustment,
):
    inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 20,
        }
    }

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: {
            "SKU-101": {
                "product_name": "Wireless Mouse",
                "quantity": 15,
            }
        },
    )

    def update_online(sku, quantity):
        inventory[sku]["quantity"] = quantity

        return {
            "sku": sku,
            "new_quantity": quantity,
            "status": "updated",
        }

    def update_erp(sku, quantity):
        raise RuntimeError("Simulated ERP failure")

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        update_online,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        update_erp,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="execution failed"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    execution = execution_service.get_execution("approval-test-001")

    assert execution["status"] == "partial_failure"
    assert execution["updated_services"] == ["online_store"]

    assert inventory["SKU-101"]["quantity"] == 18

def test_online_store_failure_records_failed_execution(
    monkeypatch,
    approved_adjustment,
):
    """An Online Store failure must prevent the ERP update."""

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: {
            "SKU-101": {"product_name": "Wireless Mouse", "quantity": 20}
        },
    )
    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: {
            "SKU-101": {"product_name": "Wireless Mouse", "quantity": 15}
        },
    )

    def fail_online_update(sku, quantity):
        raise RuntimeError("Simulated Online Store failure")

    def unexpected_erp_update(sku, quantity):
        pytest.fail("ERP must not be updated after Online Store failure")

    monkeypatch.setattr(
        execution_service, "update_online_inventory", fail_online_update
    )
    monkeypatch.setattr(
        execution_service, "update_erp_inventory", unexpected_erp_update
    )
    monkeypatch.setattr(
        execution_service, "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="execution failed"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    execution = execution_service.get_execution("approval-test-001")

    assert execution["status"] == "failed"
    assert execution["updated_services"] == []


def test_final_verification_failure_records_partial_failure(
    monkeypatch,
    approved_adjustment,
):
    """A wrong final ERP quantity must prevent successful completion."""

    online_inventory = {
        "SKU-101": {"product_name": "Wireless Mouse", "quantity": 20}
    }
    erp_inventory = {
        "SKU-101": {"product_name": "Wireless Mouse", "quantity": 15}
    }

    erp_fetch_count = 0

    def fetch_erp():
        nonlocal erp_fetch_count
        erp_fetch_count += 1

        if erp_fetch_count == 1:
            return erp_inventory

        return {
            "SKU-101": {"product_name": "Wireless Mouse", "quantity": 17}
        }

    monkeypatch.setattr(
        execution_service, "fetch_online_inventory",
        lambda: online_inventory,
    )
    monkeypatch.setattr(
        execution_service, "fetch_erp_inventory", fetch_erp,
    )

    def update_online(sku, quantity):
        online_inventory[sku]["quantity"] = quantity
        return {"sku": sku, "new_quantity": quantity, "status": "updated"}

    def update_erp(sku, quantity):
        erp_inventory[sku]["quantity"] = quantity
        return {"sku": sku, "new_quantity": quantity, "status": "updated"}

    monkeypatch.setattr(
        execution_service, "update_online_inventory", update_online,
    )
    monkeypatch.setattr(
        execution_service, "update_erp_inventory", update_erp,
    )
    monkeypatch.setattr(
        execution_service, "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="execution failed"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    execution = execution_service.get_execution("approval-test-001")

    assert execution["status"] == "verification_failed"
    assert execution["verification_passed"] is False
    assert execution["updated_services"] == ["online_store", "erp"]


def test_initial_audit_failure_prevents_execution(
    monkeypatch,
    approved_adjustment,
):
    """Execution must not start if its initial audit event cannot be written."""

    def fail_audit(*args, **kwargs):
        raise OSError("Simulated audit storage failure")

    monkeypatch.setattr(
        execution_service, "record_audit_event", fail_audit,
    )

    with pytest.raises(OSError, match="audit storage failure"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    assert execution_service.get_execution("approval-test-001") is None


def test_invalid_physical_count_prevents_execution(
    approved_adjustment,
    monkeypatch,
):
    """The target quantity must match the recorded physical count."""

    approved_adjustment["proposed_changes"]["target_quantity"] = 19

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(
        ValueError,
        match="Target quantity must match the physical count",
    ):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    assert execution_service.get_execution("approval-test-001") is None


@pytest.mark.parametrize("missing_system", ["online", "erp"])
def test_missing_sku_prevents_execution(
    monkeypatch,
    approved_adjustment,
    missing_system,
):
    """Execution must stop if the SKU is missing from either system."""

    online_inventory = (
        {}
        if missing_system == "online"
        else {
            "SKU-101": {
                "product_name": "Wireless Mouse",
                "quantity": 20,
            }
        }
    )

    erp_inventory = (
        {}
        if missing_system == "erp"
        else {
            "SKU-101": {
                "product_name": "Wireless Mouse",
                "quantity": 15,
            }
        }
    )

    monkeypatch.setattr(
        execution_service, "fetch_online_inventory",
        lambda: online_inventory,
    )
    monkeypatch.setattr(
        execution_service, "fetch_erp_inventory",
        lambda: erp_inventory,
    )
    monkeypatch.setattr(
        execution_service, "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="execution failed"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    execution = execution_service.get_execution("approval-test-001")

    assert execution["status"] == "failed"
    assert execution["updated_services"] == []


def test_online_update_succeeds_but_response_is_lost(
    monkeypatch,
    approved_adjustment,
):
    """Detect an update that succeeded remotely despite a timeout."""

    online_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 20,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 15,
        }
    }

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: online_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def update_online_then_timeout(sku, quantity):
        # The remote system changes stock successfully.
        online_inventory[sku]["quantity"] = quantity

        # But the client never receives the response.
        raise TimeoutError("Response lost after remote update")

    def unexpected_erp_update(sku, quantity):
        pytest.fail(
            "ERP must not be updated after an uncertain Online Store update"
        )

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        update_online_then_timeout,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        unexpected_erp_update,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="execution failed"):
        execution_service.execute_approved_inventory_adjustment(
            "approval-test-001"
        )

    execution = execution_service.get_execution("approval-test-001")

    # Reconciliation should discover that Online Store actually changed.
    assert execution["status"] == "partial_failure"
    assert execution["updated_services"] == ["online_store"]

    assert online_inventory["SKU-101"]["quantity"] == 18
    assert erp_inventory["SKU-101"]["quantity"] == 15



def test_erp_update_succeeds_but_response_is_lost(
    monkeypatch,
    approved_adjustment,
):
    """Detect an ERP update that succeeded despite a timeout."""

    online_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 20,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 15,
        }
    }

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: online_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def update_online(sku, quantity):
        online_inventory[sku]["quantity"] = quantity

        return {
            "sku": sku,
            "new_quantity": quantity,
            "status": "updated",
        }

    def update_erp_then_timeout(sku, quantity):
        erp_inventory[sku]["quantity"] = quantity
        raise TimeoutError("ERP response lost after remote update")

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        update_online,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        update_erp_then_timeout,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    result = execution_service.execute_approved_inventory_adjustment(
        "approval-test-001"
    )

    assert result["status"] == "reconciled"
    assert result["verification_passed"] is True
    assert result["updated_services"] == ["online_store", "erp"]

    assert result["observed_quantities"] == {
        "online_store": 18,
        "erp": 18,
    }

    assert online_inventory["SKU-101"]["quantity"] == 18
    assert erp_inventory["SKU-101"]["quantity"] == 18


def test_recovery_updates_only_the_outstanding_system(
    monkeypatch,
    approved_adjustment,
):
    """Recovery must not repeat an update already confirmed successful."""

    online_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 18,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 15,
        }
    }

    # Simulate an earlier partial execution.
    execution = {
        "approval_id": "approval-test-001",
        "status": "partial_failure",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store"],
        "verification_passed": False,
        "observed_quantities": {
            "online_store": 18,
            "erp": 15,
        },
        "failure_type": "RuntimeError",
        "failure_message": "ERP update failed",
        "completed_at": None,
    }

    with execution_service._execution_lock:
        execution_service._EXECUTIONS["approval-test-001"] = execution

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: online_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def unexpected_online_update(sku, quantity):
        pytest.fail(
            "Online Store must not be updated again during recovery"
        )

    def update_erp(sku, quantity):
        erp_inventory[sku]["quantity"] = quantity

        return {
            "sku": sku,
            "new_quantity": quantity,
            "status": "updated",
        }

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        unexpected_online_update,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        update_erp,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    result = execution_service.recover_partial_inventory_execution(
        "approval-test-001"
    )

    assert result["status"] == "recovered"
    assert result["verification_passed"] is True
    assert result["updated_services"] == ["online_store", "erp"]

    assert online_inventory["SKU-101"]["quantity"] == 18
    assert erp_inventory["SKU-101"]["quantity"] == 18


def test_recovery_stops_when_a_system_has_an_unexpected_quantity(
    monkeypatch,
    approved_adjustment,
):
    """Recovery must never overwrite inventory changed unexpectedly."""

    online_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 18,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 16,
        }
    }

    execution = {
        "approval_id": "approval-test-001",
        "status": "partial_failure",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store"],
        "verification_passed": False,
        "observed_quantities": {
            "online_store": 18,
            "erp": 15,
        },
        "failure_type": "RuntimeError",
        "failure_message": "ERP update failed",
        "completed_at": None,
    }

    with execution_service._execution_lock:
        execution_service._EXECUTIONS["approval-test-001"] = execution

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: online_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def unexpected_update(sku, quantity):
        pytest.fail("Recovery must not update either system")

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        unexpected_update,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        unexpected_update,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="Inventory recovery failed"):
        execution_service.recover_partial_inventory_execution(
            "approval-test-001"
        )

    result = execution_service.get_execution("approval-test-001")

    assert result["status"] == "partial_failure"
    assert result["verification_passed"] is False

    assert result["observed_quantities"] == {
        "online_store": 18,
        "erp": 16,
    }

    # Neither system was changed.
    assert online_inventory["SKU-101"]["quantity"] == 18
    assert erp_inventory["SKU-101"]["quantity"] == 16


def test_recovery_does_not_repeat_erp_update_when_response_is_lost(
    monkeypatch,
    approved_adjustment,
):
    """Recovery recognises an ERP update that succeeded despite a timeout."""

    online_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 18,
        }
    }

    erp_inventory = {
        "SKU-101": {
            "product_name": "Wireless Mouse",
            "quantity": 15,
        }
    }

    execution = {
        "approval_id": "approval-test-001",
        "status": "partial_failure",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store"],
        "verification_passed": False,
        "observed_quantities": {
            "online_store": 18,
            "erp": 15,
        },
        "failure_type": "TimeoutError",
        "failure_message": "ERP response timed out",
        "completed_at": None,
    }

    with execution_service._execution_lock:
        execution_service._EXECUTIONS["approval-test-001"] = execution

    monkeypatch.setattr(
        execution_service,
        "fetch_online_inventory",
        lambda: online_inventory,
    )

    monkeypatch.setattr(
        execution_service,
        "fetch_erp_inventory",
        lambda: erp_inventory,
    )

    def unexpected_online_update(sku, quantity):
        pytest.fail("Online Store must not be updated again")

    def update_erp_then_lose_response(sku, quantity):
        erp_inventory[sku]["quantity"] = quantity
        raise TimeoutError("ERP response timed out")

    monkeypatch.setattr(
        execution_service,
        "update_online_inventory",
        unexpected_online_update,
    )

    monkeypatch.setattr(
        execution_service,
        "update_erp_inventory",
        update_erp_then_lose_response,
    )

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    # First recovery attempt: ERP updates successfully, but response is lost.
    with pytest.raises(RuntimeError, match="Inventory recovery failed"):
        execution_service.recover_partial_inventory_execution(
            "approval-test-001"
        )

    assert erp_inventory["SKU-101"]["quantity"] == 18

    # Second attempt: recovery discovers ERP is already at the target.
    result = execution_service.recover_partial_inventory_execution(
        "approval-test-001"
    )

    assert result["status"] == "recovered"
    assert result["verification_passed"] is True
    assert result["updated_services"] == ["online_store", "erp"]

    assert online_inventory["SKU-101"]["quantity"] == 18
    assert erp_inventory["SKU-101"]["quantity"] == 18


def test_recovery_rejects_concurrent_attempt_for_same_approval(
    monkeypatch,
    approved_adjustment,
):
    """Only one recovery attempt can run for an approval at a time."""

    execution = {
        "approval_id": "approval-test-001",
        "status": "partial_failure",
        "sku": "SKU-101",
        "target_quantity": 18,
        "updated_services": ["online_store"],
        "verification_passed": False,
        "observed_quantities": {
            "online_store": 18,
            "erp": 15,
        },
        "failure_type": "RuntimeError",
        "failure_message": "ERP update failed",
        "completed_at": None,
    }

    with execution_service._execution_lock:
        execution_service._EXECUTIONS["approval-test-001"] = execution
        execution_service._RECOVERING.add("approval-test-001")

    monkeypatch.setattr(
        execution_service,
        "record_audit_event",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(
        ValueError,
        match="A recovery attempt is already running",
    ):
        execution_service.recover_partial_inventory_execution(
            "approval-test-001"
        )

    # The existing recovery attempt must remain untouched.
    assert (
        "approval-test-001"
        in execution_service._RECOVERING
    )

    result = execution_service.get_execution("approval-test-001")

    assert result["status"] == "partial_failure"
