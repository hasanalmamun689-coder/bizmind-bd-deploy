import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Supplier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "suppliers"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Evidence fields shown transparently to the user rather than collapsed
    # into a single opaque score (section 15).
    delivery_time_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    reliability_score: Mapped[float] = mapped_column(Numeric(5, 2), default=80.0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Numeric(5, 2), default=80.0, nullable=False)
    fulfillment_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=95.0, nullable=False)
    payment_terms: Mapped[str | None] = mapped_column(String(120), nullable=True)

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")  # noqa: F821


class SupplierProduct(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Price/MOQ a specific supplier offers for a specific product."""

    __tablename__ = "supplier_products"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SupplierPriceHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Append-only log of every price a supplier quoted for a product. Lets the
    risk engine detect real supplier price increases (section 21) instead of
    guessing from a single current price.
    """

    __tablename__ = "supplier_price_history"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
