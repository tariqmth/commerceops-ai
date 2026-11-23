
from typing import Literal

from pydantic import BaseModel, Field


class InventoryDiscrepancy(BaseModel):
    sku: str
    product_name: str | None = None
    online_quantity: int | None = None
    erp_quantity: int | None = None
    difference: int | None = None
    status: Literal["matched", "discrepancy", "missing_from_system"]


class InventoryRecord(BaseModel):
    product_name: str = Field(min_length=1)
    quantity: int = Field(ge=0, strict=True)


class InventoryComparisonRequest(BaseModel):
    online_store: dict[str, InventoryRecord]
    erp_system: dict[str, InventoryRecord]


class AIQuestionRequest(BaseModel):
    question: str = Field(min_length=1)

class ApprovalCreateRequest(BaseModel):
    action_type: Literal[
        "inventory_adjustment",
        "order_cancellation",
        "refund",
    ]

    description: str = Field(min_length=1)
    proposed_changes: dict = Field(min_length=1)


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    decided_by: str = Field(min_length=1)
    role: str = Field(min_length=1)
    comment: str = ""