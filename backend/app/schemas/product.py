import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.catalog import ProductStatus


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=64)
    category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    brand: str | None = None
    unit: str = "pcs"
    purchase_price: float = Field(ge=0)
    selling_price: float = Field(ge=0)
    current_stock: int = Field(ge=0, default=0)
    minimum_stock: int = Field(ge=0, default=0)
    maximum_stock: int = Field(ge=0, default=0)
    expiry_date: date | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    brand: str | None = None
    unit: str | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    selling_price: float | None = Field(default=None, ge=0)
    minimum_stock: int | None = Field(default=None, ge=0)
    maximum_stock: int | None = Field(default=None, ge=0)
    expiry_date: date | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    sku: str
    category_id: uuid.UUID | None
    supplier_id: uuid.UUID | None
    brand: str | None
    unit: str
    purchase_price: float
    selling_price: float
    current_stock: int
    minimum_stock: int
    maximum_stock: int
    expiry_date: date | None
    status: ProductStatus
    is_active: bool
    profit_per_unit: float
    margin_percent: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}
