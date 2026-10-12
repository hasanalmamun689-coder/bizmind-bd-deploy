import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact: str | None = None
    location: str | None = None
    delivery_time_days: int = Field(default=3, ge=0)
    reliability_score: float = Field(default=80.0, ge=0, le=100)
    quality_score: float = Field(default=80.0, ge=0, le=100)
    fulfillment_rate: float = Field(default=95.0, ge=0, le=100)
    payment_terms: str | None = None


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    contact: str | None
    location: str | None
    delivery_time_days: int
    reliability_score: float
    quality_score: float
    fulfillment_rate: float
    payment_terms: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierComparisonRow(BaseModel):
    supplier: SupplierOut
    price: float | None
    minimum_order_quantity: int | None
    composite_note: str


class SupplierPriceSet(BaseModel):
    product_id: uuid.UUID
    price: float = Field(ge=0)
    minimum_order_quantity: int = Field(default=1, ge=1)
