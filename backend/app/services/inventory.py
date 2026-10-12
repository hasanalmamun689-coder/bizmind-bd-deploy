"""
section 11/13/47: every stock movement goes through here so that
current_stock, the ledger, product status, and low-stock alerts all stay
consistent no matter which module triggered the change.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductStatus
from app.models.intelligence import Alert, AlertSeverity
from app.models.inventory import InventoryTransaction, InventoryTransactionType


def apply_stock_change(
    db: Session,
    *,
    business_id: uuid.UUID,
    product: Product,
    delta: int,
    txn_type: InventoryTransactionType,
    created_by: uuid.UUID | None,
    reason: str | None = None,
    related_sale_id: uuid.UUID | None = None,
) -> InventoryTransaction:
    product.current_stock += delta
    if product.current_stock < 0:
        product.current_stock = 0

    previous_status = product.status
    product.recompute_status()

    txn = InventoryTransaction(
        business_id=business_id,
        product_id=product.id,
        created_by=created_by,
        type=txn_type,
        quantity_delta=delta,
        resulting_stock=product.current_stock,
        reason=reason,
        related_sale_id=related_sale_id,
    )
    db.add(txn)

    # Generate a low-stock / stockout alert exactly when the status
    # transitions into a worse state, so we don't spam duplicate alerts
    # on every subsequent sale (section 20).
    worsened = previous_status != product.status and product.status in (
        ProductStatus.LOW_STOCK,
        ProductStatus.CRITICAL,
        ProductStatus.OUT_OF_STOCK,
    )
    if worsened:
        severity = (
            AlertSeverity.CRITICAL
            if product.status in (ProductStatus.CRITICAL, ProductStatus.OUT_OF_STOCK)
            else AlertSeverity.WARNING
        )
        db.add(
            Alert(
                business_id=business_id,
                type="inventory",
                severity=severity,
                title=f"{product.name} is {product.status.value.replace('_', ' ')}",
                description=(
                    f"Current stock for {product.name} ({product.sku}) is {product.current_stock}, "
                    f"below its minimum threshold of {product.minimum_stock}."
                ),
                related_entity_type="product",
                related_entity_id=product.id,
                suggested_action="Review demand and consider creating a purchase order.",
            )
        )

    db.flush()
    return txn
