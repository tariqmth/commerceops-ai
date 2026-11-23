
"""Role-based permissions for CommerceOps approval decisions."""

ROLE_PERMISSIONS = {
    "warehouse_manager": {
        "inventory_adjustment",
    },
    "operations_manager": {
        "inventory_adjustment",
        "order_cancellation",
    },
    "finance_manager": {
        "refund",
    },
    "admin": {
        "inventory_adjustment",
        "order_cancellation",
        "refund",
    },
}


def can_approve(role: str, action_type: str) -> bool:
    """Check whether a role can approve a particular action type."""

    permissions = ROLE_PERMISSIONS.get(role)

    if permissions is None:
        return False

    return action_type in permissions
