import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.sales import SaleStatus


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)


class SaleCreate(BaseModel):
    customer_id: uuid.UUID | None = None
    payment_method: str = "cash"
    items: list[SaleItemCreate] = Field(min_length=1)


class SaleItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: float
    unit_cost: float
    subtotal: float

    model_config = {"from_attributes": True}


class SaleOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID | None
    total_amount: float
    total_cost: float
    gross_profit: float
    payment_method: str
    status: SaleStatus
    created_at: datetime
    items: list[SaleItemOut]

    model_config = {"from_attributes": True}


class SalesSummary(BaseModel):
    total_revenue: float
    total_cost: float
    gross_profit: float
    total_transactions: int
    average_order_value: float
