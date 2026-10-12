import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.inventory import InventoryTransactionType


class InventoryAdjustRequest(BaseModel):
    product_id: uuid.UUID
    type: InventoryTransactionType
    quantity: int = Field(gt=0)
    # Only used for type=adjustment (stock_in always adds, stock_out always removes).
    direction: Literal["increase", "decrease"] = "decrease"
    reason: str | None = None


class InventoryTransactionOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    type: InventoryTransactionType
    quantity_delta: int
    resulting_stock: int
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
