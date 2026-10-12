import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact: str | None = None


class CustomerOut(BaseModel):
    id: uuid.UUID
    name: str
    contact: str | None
    created_at: datetime
    # Derived analytics fields (not stored):
    total_spent: float = 0
    total_orders: int = 0
    last_purchase_at: datetime | None = None
    segment: str = "new"

    model_config = {"from_attributes": True}
