
import pytest

from integrations.approval_permissions import can_approve


@pytest.mark.parametrize(
    "role, action_type, expected",
    [
        ("warehouse_manager", "inventory_adjustment", True),
        ("warehouse_manager", "refund", False),
        ("warehouse_manager", "order_cancellation", False),
        ("operations_manager", "inventory_adjustment", True),
        ("operations_manager", "order_cancellation", True),
        ("operations_manager", "refund", False),
        ("finance_manager", "refund", True),
        ("finance_manager", "inventory_adjustment", False),
        ("admin", "inventory_adjustment", True),
        ("admin", "order_cancellation", True),
        ("admin", "refund", True),
        ("unknown_role", "refund", False),
    ],
)
def test_role_permissions(role, action_type, expected):
    assert can_approve(role, action_type) is expected
