import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "categories"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class ProductStatus(str, enum.Enum):
    HEALTHY = "healthy"
    LOW_STOCK = "low_stock"
    CRITICAL = "critical"
    OUT_OF_STOCK = "out_of_stock"
    OVERSTOCK = "overstock"


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"
    # A SKU identifies exactly one product within a business (different businesses may reuse a SKU).
    __table_args__ = (UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="pcs", nullable=False)

    purchase_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    current_stock: Mapped[int] = mapped_column(default=0, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(default=0, nullable=False)
    maximum_stock: Mapped[int] = mapped_column(default=0, nullable=False)

    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), default=ProductStatus.HEALTHY, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    category: Mapped["Category | None"] = relationship()
    supplier: Mapped["Supplier | None"] = relationship(back_populates="products")  # noqa: F821

    @property
    def profit_per_unit(self) -> float:
        return float(self.selling_price) - float(self.purchase_price)

    @property
    def margin_percent(self) -> float:
        if not self.selling_price:
            return 0.0
        return round((self.profit_per_unit / float(self.selling_price)) * 100, 2)

    def recompute_status(self) -> None:
        """Derive stock status from current vs min/max thresholds (section 13)."""
        if self.current_stock <= 0:
            self.status = ProductStatus.OUT_OF_STOCK
        elif self.current_stock < self.minimum_stock * 0.5:
            self.status = ProductStatus.CRITICAL
        elif self.current_stock < self.minimum_stock:
            self.status = ProductStatus.LOW_STOCK
        elif self.maximum_stock and self.current_stock > self.maximum_stock:
            self.status = ProductStatus.OVERSTOCK
        else:
            self.status = ProductStatus.HEALTHY
