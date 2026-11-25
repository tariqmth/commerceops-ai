
"""Controlled execution of approved CommerceOps inventory adjustments."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock

from integrations import approval_service
from integrations.audit_log import record_audit_event
from integrations.online_store_client import (
    fetch_online_inventory,
    update_online_inventory,
)
from integrations.erp_client import (
    fetch_erp_inventory,
    update_erp_inventory,
)

_EXECUTIONS: dict[str, dict] = {}

_execution_lock = Lock()

# Prevent two recovery attempts for the same approval at once.
_RECOVERING: set[str] = set()

def _validate_proposed_changes(changes: dict) -> dict:
    """Validate an approved inventory adjustment proposal."""

    required_fields = {
        "sku",
        "target_quantity",
        "physical_count",
        "count_reference",
        "reason",
        "expected_online_quantity",
        "expected_erp_quantity",
    }

    if not isinstance(changes, dict):
        raise ValueError("Proposed changes must be a dictionary")

    if set(changes) != required_fields:
        raise ValueError("Invalid inventory adjustment fields")

    sku = changes["sku"]

    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("SKU cannot be empty")

    quantity_fields = (
        "target_quantity",
        "physical_count",
        "expected_online_quantity",
        "expected_erp_quantity",
    )

    for field in quantity_fields:
        value = changes[field]

        if type(value) is not int or value < 0:
            raise ValueError(
                f"{field} must be a non-negative integer"
            )

    if changes["target_quantity"] != changes["physical_count"]:
        raise ValueError(
            "Target quantity must match the physical count"
        )

    for field in ("count_reference", "reason"):
        value = changes[field]

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} cannot be empty")

    return deepcopy(changes)


def get_execution(approval_id: str) -> dict | None:
    """Retrieve the execution record for an approval."""

    with _execution_lock:
        execution = _EXECUTIONS.get(approval_id)

        return deepcopy(execution) if execution else None


def execute_approved_inventory_adjustment(
    approval_id: str,
) -> dict:
    """Execute and independently verify an approved inventory adjustment."""

    if not isinstance(approval_id, str) or not approval_id.strip():
        raise ValueError("Approval ID cannot be empty")

    with _execution_lock:
        if approval_id in _EXECUTIONS:
            raise ValueError(
                "An execution attempt already exists for this approval"
            )

        approval = approval_service.get_approval(approval_id)

        if approval is None:
            raise ValueError("Approval not found")

        if approval["status"] != "approved":
            raise ValueError("Approval must be approved before execution")

        if approval["action_type"] != "inventory_adjustment":
            raise ValueError(
                "Only inventory adjustments can be executed here"
            )

        changes = _validate_proposed_changes(
            approval["proposed_changes"]
        )

        execution = {
            "approval_id": approval_id,
            "status": "in_progress",
            "sku": changes["sku"],
            "target_quantity": changes["target_quantity"],
            "updated_services": [],
            "verification_passed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "failure_type": None,
            "failure_message": None,
            "observed_quantities": None,
            "reconciliation_error": None,
            "recovery_attempts": 0,
            "recovered_at": None,
            "last_recovery_error": None,
        }

        # Audit before any inventory changes.
        record_audit_event(
            "inventory_execution_started",
            {
                "approval_id": approval_id,
                "sku": changes["sku"],
                "target_quantity": changes["target_quantity"],
                "count_reference": changes["count_reference"],
            },
        )

        _EXECUTIONS[approval_id] = execution

    updated_services = []
    verification_passed = False

    try:
        sku = changes["sku"]
        target_quantity = changes["target_quantity"]

        # 1. Fetch both systems before making any changes.
        online_inventory = fetch_online_inventory()
        erp_inventory = fetch_erp_inventory()

        if sku not in online_inventory:
            raise ValueError("SKU is missing from the Online Store")

        if sku not in erp_inventory:
            raise ValueError("SKU is missing from the ERP")

        # 2. Check for changes since approval.
        if (
            online_inventory[sku]["quantity"]
            != changes["expected_online_quantity"]
        ):
            raise ValueError(
                "Online Store inventory changed since approval"
            )

        if (
            erp_inventory[sku]["quantity"]
            != changes["expected_erp_quantity"]
        ):
            raise ValueError(
                "ERP inventory changed since approval"
            )

        record_audit_event(
            "inventory_pre_execution_check_passed",
            {
                "approval_id": approval_id,
                "sku": sku,
                "online_quantity": online_inventory[sku]["quantity"],
                "erp_quantity": erp_inventory[sku]["quantity"],
            },
        )

        # 3. Update the Online Store.
        online_result = update_online_inventory(
            sku=sku,
            quantity=target_quantity,
        )

        if (
            online_result.get("status") != "updated"
            or online_result.get("sku") != sku
            or online_result.get("new_quantity") != target_quantity
        ):
            raise RuntimeError(
                "Online Store update response could not be verified"
            )

        updated_services.append("online_store")

        # 4. Update the ERP.
        erp_result = update_erp_inventory(
            sku=sku,
            quantity=target_quantity,
        )

        if (
            erp_result.get("status") != "updated"
            or erp_result.get("sku") != sku
            or erp_result.get("new_quantity") != target_quantity
        ):
            raise RuntimeError(
                "ERP update response could not be verified"
            )

        updated_services.append("erp")

        # 5. Fetch both systems again to verify the final state.
        verified_online = fetch_online_inventory()
        verified_erp = fetch_erp_inventory()

        online_final = verified_online.get(sku)
        erp_final = verified_erp.get(sku)

        if online_final is None or erp_final is None:
            raise RuntimeError(
                "SKU missing during final inventory verification"
            )

        if online_final["quantity"] != target_quantity:
            raise RuntimeError(
                "Online Store final quantity verification failed"
            )

        if erp_final["quantity"] != target_quantity:
            raise RuntimeError(
                "ERP final quantity verification failed"
            )

        verification_passed = True

        # 6. Record successful execution.
        record_audit_event(
            "inventory_execution_completed",
            {
                "approval_id": approval_id,
                "sku": sku,
                "target_quantity": target_quantity,
                "count_reference": changes["count_reference"],
                "verified_online_quantity": online_final["quantity"],
                "verified_erp_quantity": erp_final["quantity"],
            },
        )

        with _execution_lock:
            execution = _EXECUTIONS[approval_id]

            execution["status"] = "completed"
            execution["updated_services"] = list(updated_services)
            execution["verification_passed"] = True
            execution["completed_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

            return deepcopy(execution)

    except Exception as exc:
        # Reconcile actual remote state after an execution error.
        observed_quantities = {}
        reconciliation_error = None

        try:
            online_inventory = fetch_online_inventory()
            erp_inventory = fetch_erp_inventory()

            online_record = online_inventory.get(sku)
            erp_record = erp_inventory.get(sku)

            observed_quantities = {
                "online_store": (
                    online_record.get("quantity")
                    if online_record is not None
                    else None
                ),
                "erp": (
                    erp_record.get("quantity")
                    if erp_record is not None
                    else None
                ),
            }

            # Record an update only when the approved target is
            # observed and the approved starting quantity differed.
            if (
                changes["expected_online_quantity"] != target_quantity
                and observed_quantities["online_store"] == target_quantity
                and "online_store" not in updated_services
            ):
                updated_services.append("online_store")

            if (
                changes["expected_erp_quantity"] != target_quantity
                and observed_quantities["erp"] == target_quantity
                and "erp" not in updated_services
            ):
                updated_services.append("erp")

        except Exception as reconciliation_exc:
            reconciliation_error = str(reconciliation_exc)

        # Both systems have independently confirmed the target quantity.
        both_at_target = (
            observed_quantities.get("online_store") == target_quantity
            and observed_quantities.get("erp") == target_quantity
        )

        if both_at_target:
            verification_passed = True

            try:
                # Audit the successful reconciliation before reporting it.
                record_audit_event(
                    "inventory_execution_reconciled",
                    {
                        "approval_id": approval_id,
                        "sku": sku,
                        "target_quantity": target_quantity,
                        "count_reference": changes["count_reference"],
                        "updated_services": list(updated_services),
                        "observed_quantities": observed_quantities,
                        "original_failure_type": type(exc).__name__,
                        "original_failure_message": str(exc),
                    },
                )

            except Exception as audit_exc:
                reconciliation_error = (
                    "Both systems reached the target quantity, "
                    "but reconciliation audit recording failed: "
                    f"{audit_exc}"
                )

                failure_status = "audit_failure"

            else:
                with _execution_lock:
                    execution = _EXECUTIONS[approval_id]

                    execution["status"] = "reconciled"
                    execution["updated_services"] = list(updated_services)
                    execution["verification_passed"] = True
                    execution["observed_quantities"] = observed_quantities
                    execution["reconciliation_error"] = None
                    execution["failure_type"] = type(exc).__name__
                    execution["failure_message"] = str(exc)
                    execution["completed_at"] = (
                        datetime.now(timezone.utc).isoformat()
                    )

                    return deepcopy(execution)

        else:
            # Classify the failure using confirmed remote state.
            if len(updated_services) == 0:
                failure_status = "failed"
            elif len(updated_services) == 1:
                failure_status = "partial_failure"
            elif not verification_passed:
                failure_status = "verification_failed"
            else:
                failure_status = "audit_failure"

        with _execution_lock:
            execution = _EXECUTIONS[approval_id]
            execution["status"] = failure_status
            execution["updated_services"] = list(updated_services)
            execution["verification_passed"] = verification_passed
            execution["failure_type"] = type(exc).__name__
            execution["failure_message"] = str(exc)
            execution["observed_quantities"] = observed_quantities
            execution["reconciliation_error"] = reconciliation_error

        try:
            record_audit_event(
                "inventory_execution_failed",
                {
                    "approval_id": approval_id,
                    "status": failure_status,
                    "updated_services": list(updated_services),
                    "verification_passed": verification_passed,
                    "observed_quantities": observed_quantities,
                    "reconciliation_error": reconciliation_error,
                    "failure_type": type(exc).__name__,
                    "failure_message": str(exc),
                },
            )
        except Exception:
            # Preserve the original execution failure.
            pass

        raise RuntimeError(
            "Inventory adjustment execution failed. "
            "Inspect the execution record and reconcile both systems "
            "before attempting another adjustment."
        ) from exc


def recover_partial_inventory_execution(approval_id: str) -> dict:
    """Safely resume an approved inventory execution after partial failure."""

    if not isinstance(approval_id, str) or not approval_id.strip():
        raise ValueError("Approval ID cannot be empty")

    # Reserve this recovery attempt and take a safe snapshot.
    with _execution_lock:
        execution = _EXECUTIONS.get(approval_id)

        if execution is None:
            raise ValueError("Execution record not found")

        if execution["status"] != "partial_failure":
            raise ValueError(
                "Only partial failures can be recovered"
            )

        if approval_id in _RECOVERING:
            raise ValueError(
                "A recovery attempt is already running"
            )

        _RECOVERING.add(approval_id)
        execution_snapshot = deepcopy(execution)

    attempt_number = execution_snapshot.get(
        "recovery_attempts", 0
    ) + 1

    updated_services = list(
        execution_snapshot.get("updated_services", [])
    )

    observed_quantities = {}

    try:
        # 1. Re-check the original human approval.
        approval = approval_service.get_approval(approval_id)

        if approval is None:
            raise ValueError("Approval not found")

        if approval["status"] != "approved":
            raise ValueError(
                "Approval must remain approved during recovery"
            )

        if approval["action_type"] != "inventory_adjustment":
            raise ValueError(
                "Only inventory adjustments can be recovered"
            )

        changes = _validate_proposed_changes(
            approval["proposed_changes"]
        )

        sku = changes["sku"]
        target_quantity = changes["target_quantity"]

        if (
            execution_snapshot["sku"] != sku
            or execution_snapshot["target_quantity"] != target_quantity
        ):
            raise ValueError(
                "Execution record does not match the approved proposal"
            )

        # 2. Audit the start before contacting either inventory system.
        record_audit_event(
            "inventory_recovery_started",
            {
                "approval_id": approval_id,
                "sku": sku,
                "target_quantity": target_quantity,
                "attempt_number": attempt_number,
                "count_reference": changes["count_reference"],
            },
        )

        # 3. Fetch both systems before making any changes.
        online_inventory = fetch_online_inventory()
        erp_inventory = fetch_erp_inventory()

        online_record = online_inventory.get(sku)
        erp_record = erp_inventory.get(sku)

        if online_record is None:
            raise ValueError(
                "SKU is missing from the Online Store"
            )

        if erp_record is None:
            raise ValueError("SKU is missing from the ERP")

        online_quantity = online_record["quantity"]
        erp_quantity = erp_record["quantity"]

        observed_quantities = {
            "online_store": online_quantity,
            "erp": erp_quantity,
        }

        # 4. Only approved original or target quantities are safe.
        expected_online = changes["expected_online_quantity"]
        expected_erp = changes["expected_erp_quantity"]

        allowed_online = {expected_online, target_quantity}
        allowed_erp = {expected_erp, target_quantity}

        if online_quantity not in allowed_online:
            raise RuntimeError(
                "Online Store quantity is unexpected. "
                "Recovery stopped without making updates."
            )

        if erp_quantity not in allowed_erp:
            raise RuntimeError(
                "ERP quantity is unexpected. "
                "Recovery stopped without making updates."
            )

        record_audit_event(
            "inventory_recovery_precheck_passed",
            {
                "approval_id": approval_id,
                "sku": sku,
                "online_quantity": online_quantity,
                "erp_quantity": erp_quantity,
            },
        )

        # 5. Update only systems still at their approved original quantity.
        if online_quantity == expected_online and (
            expected_online != target_quantity
        ):
            online_result = update_online_inventory(
                sku=sku,
                quantity=target_quantity,
            )

            if (
                online_result.get("status") != "updated"
                or online_result.get("sku") != sku
                or online_result.get("new_quantity") != target_quantity
            ):
                raise RuntimeError(
                    "Online Store recovery update could not be verified"
                )

        if erp_quantity == expected_erp and (
            expected_erp != target_quantity
        ):
            erp_result = update_erp_inventory(
                sku=sku,
                quantity=target_quantity,
            )

            if (
                erp_result.get("status") != "updated"
                or erp_result.get("sku") != sku
                or erp_result.get("new_quantity") != target_quantity
            ):
                raise RuntimeError(
                    "ERP recovery update could not be verified"
                )

        # 6. Fetch both systems again and independently verify.
        verified_online = fetch_online_inventory()
        verified_erp = fetch_erp_inventory()

        online_final = verified_online.get(sku)
        erp_final = verified_erp.get(sku)

        if online_final is None or erp_final is None:
            raise RuntimeError(
                "SKU missing during recovery verification"
            )

        observed_quantities = {
            "online_store": online_final["quantity"],
            "erp": erp_final["quantity"],
        }

        if (
            observed_quantities["online_store"] != target_quantity
            or observed_quantities["erp"] != target_quantity
        ):
            raise RuntimeError(
                "Recovery verification failed: "
                "both systems have not reached the approved target"
            )

        # Record systems confirmed at the approved target.
        if "online_store" not in updated_services:
            updated_services.append("online_store")

        if "erp" not in updated_services:
            updated_services.append("erp")

        # 7. Audit success before marking the execution recovered.
        record_audit_event(
            "inventory_recovery_completed",
            {
                "approval_id": approval_id,
                "sku": sku,
                "target_quantity": target_quantity,
                "attempt_number": attempt_number,
                "updated_services": updated_services,
                "observed_quantities": observed_quantities,
                "count_reference": changes["count_reference"],
            },
        )

        # 8. Save the recovered execution record.
        with _execution_lock:
            execution = _EXECUTIONS[approval_id]

            execution["status"] = "recovered"
            execution["updated_services"] = list(updated_services)
            execution["verification_passed"] = True
            execution["observed_quantities"] = observed_quantities
            execution["recovery_attempts"] = attempt_number
            execution["recovered_at"] = (
                datetime.now(timezone.utc).isoformat()
            )
            execution["last_recovery_error"] = None

            return deepcopy(execution)

    except Exception as exc:
        # Reconcile remote state even when an update response is lost.
        reconciliation_error = None

        try:
            online_inventory = fetch_online_inventory()
            erp_inventory = fetch_erp_inventory()

            online_record = online_inventory.get(
                execution_snapshot["sku"]
            )
            erp_record = erp_inventory.get(
                execution_snapshot["sku"]
            )

            observed_quantities = {
                "online_store": (
                    online_record.get("quantity")
                    if online_record is not None
                    else None
                ),
                "erp": (
                    erp_record.get("quantity")
                    if erp_record is not None
                    else None
                ),
            }

            target = execution_snapshot["target_quantity"]

            if (
                observed_quantities["online_store"] == target
                and "online_store" not in updated_services
            ):
                updated_services.append("online_store")

            if (
                observed_quantities["erp"] == target
                and "erp" not in updated_services
            ):
                updated_services.append("erp")

        except Exception as reconciliation_exc:
            reconciliation_error = str(reconciliation_exc)

        # Keep the record recoverable. A later attempt will re-check
        # both actual quantities before making any further updates.
        with _execution_lock:
            execution = _EXECUTIONS[approval_id]

            execution["status"] = "partial_failure"
            execution["updated_services"] = list(updated_services)
            execution["verification_passed"] = False
            execution["observed_quantities"] = observed_quantities
            execution["recovery_attempts"] = attempt_number
            execution["last_recovery_error"] = str(exc)
            execution["reconciliation_error"] = reconciliation_error

        try:
            record_audit_event(
                "inventory_recovery_failed",
                {
                    "approval_id": approval_id,
                    "attempt_number": attempt_number,
                    "updated_services": updated_services,
                    "observed_quantities": observed_quantities,
                    "failure_type": type(exc).__name__,
                    "failure_message": str(exc),
                    "reconciliation_error": reconciliation_error,
                },
            )
        except Exception:
            # Preserve the original recovery failure.
            pass

        raise RuntimeError(
            "Inventory recovery failed. "
            "Inspect the execution record before retrying."
        ) from exc

    finally:
        with _execution_lock:
            _RECOVERING.discard(approval_id)
