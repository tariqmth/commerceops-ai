
"""Human approval workflow for proposed CommerceOps actions."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from integrations.approval_permissions import can_approve
from integrations.audit_log import record_audit_event
from integrations.request_context import request_id_var


ALLOWED_ACTION_TYPES = {
    "inventory_adjustment",
    "order_cancellation",
    "refund",
}

_APPROVALS: dict[str, dict] = {}
_approval_lock = Lock()


def create_approval(
    action_type: str,
    description: str,
    proposed_changes: dict,
) -> dict:
    """Create a pending approval without executing the proposed action."""

    if action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError("Unsupported action type")

    if not isinstance(description, str) or not description.strip():
        raise ValueError("Description cannot be empty")

    if not isinstance(proposed_changes, dict) or not proposed_changes:
        raise ValueError("Proposed changes must be a non-empty dictionary")

    approval = {
        "approval_id": str(uuid4()),
        "request_id": request_id_var.get(),
        "action_type": action_type,
        "description": description,
        "proposed_changes": deepcopy(proposed_changes),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decided_at": None,
        "decision": None,
    }

    with _approval_lock:
        _APPROVALS[approval["approval_id"]] = approval

        try:
            record_audit_event(
                "approval_created",
                {
                    "approval_id": approval["approval_id"],
                    "action_type": action_type,
                    "status": "pending",
                },
            )
        except Exception:
            _APPROVALS.pop(approval["approval_id"], None)
            raise

        return deepcopy(approval)


def get_approval(approval_id: str) -> dict | None:
    """Return an approval by ID."""

    with _approval_lock:
        approval = _APPROVALS.get(approval_id)
        return deepcopy(approval) if approval else None


def decide_approval(
    approval_id: str,
    decision: str,
    decided_by: str,
    role: str,
    comment: str = "",
) -> dict:
    """Approve or reject a pending proposal after checking permissions.

    This function changes approval status only.
    It does not execute the proposed business action.
    """

    if decision not in {"approved", "rejected"}:
        raise ValueError("Decision must be approved or rejected")

    if not isinstance(decided_by, str) or not decided_by.strip():
        raise ValueError("Decided by cannot be empty")

    if not isinstance(role, str) or not role.strip():
        raise ValueError("Role cannot be empty")

    if not isinstance(comment, str):
        raise ValueError("Comment must be a string")

    with _approval_lock:
        approval = _APPROVALS.get(approval_id)

        if approval is None:
            raise ValueError("Approval not found")

        if approval["status"] != "pending":
            raise ValueError("Approval has already been decided")

        if not can_approve(role, approval["action_type"]):
            raise PermissionError(
                f"Role '{role}' cannot approve "
                f"'{approval['action_type']}'"
            )

        # Write the audit event BEFORE changing the approval status.
        # If audit storage fails, the approval remains pending.
        record_audit_event(
            "approval_decided",
            {
                "approval_id": approval_id,
                "decision": decision,
                "decided_by": decided_by,
                "role": role,
            },
        )

        approval["status"] = decision
        approval["decided_at"] = datetime.now(timezone.utc).isoformat()
        approval["decision"] = {
            "decided_by": decided_by,
            "role": role,
            "comment": comment,
        }

        return deepcopy(approval)
