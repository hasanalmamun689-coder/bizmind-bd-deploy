import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.procurement import PurchaseOrderSource, PurchaseOrderStatus


class PurchaseOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    expected_delivery_date: date | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderStatusUpdate(BaseModel):
    status: PurchaseOrderStatus


class PurchaseOrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class PurchaseOrderOut(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    status: PurchaseOrderStatus
    source: PurchaseOrderSource
    total_cost: float
    expected_delivery_date: date | None
    notes: str | None
    created_at: datetime
    items: list[PurchaseOrderItemOut]

    model_config = {"from_attributes": True}
