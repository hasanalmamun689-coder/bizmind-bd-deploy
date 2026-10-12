import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.catalog import Product
from app.models.intelligence import Alert, AlertStatus
from app.models.inventory import InventoryTransaction, InventoryTransactionType
from app.models.user import User, UserRole
from app.schemas.inventory import InventoryAdjustRequest, InventoryTransactionOut
from app.schemas.intelligence import AlertOut
from app.schemas.product import ProductOut
from app.services import audit
from app.services.inventory import apply_stock_change

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[ProductOut])
def inventory_list(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    products = db.scalars(
        select(Product)
        .where(Product.business_id == current_user.business_id, Product.is_active.is_(True))
        .order_by(Product.name)
    ).all()
    return [ProductOut.model_validate(p) for p in products]


@router.get("/alerts", response_model=list[AlertOut])
def inventory_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerts = db.scalars(
        select(Alert)
        .where(
            Alert.business_id == current_user.business_id,
            Alert.type == "inventory",
            Alert.status.in_([AlertStatus.UNREAD, AlertStatus.READ]),
        )
        .order_by(Alert.created_at.desc())
    ).all()
    return [AlertOut.model_validate(a) for a in alerts]


@router.post("/adjust", response_model=InventoryTransactionOut, status_code=201)
def adjust_inventory(
    payload: InventoryAdjustRequest,
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    product = db.get(Product, payload.product_id)
    if product is None or product.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Product not found.")

    if payload.type == InventoryTransactionType.STOCK_IN:
        delta = payload.quantity
    elif payload.type == InventoryTransactionType.ADJUSTMENT:
        delta = payload.quantity if payload.direction == "increase" else -payload.quantity
    else:  # stock_out (and any other outbound movement)
        delta = -payload.quantity
    txn = apply_stock_change(
        db,
        business_id=current_user.business_id,
        product=product,
        delta=delta,
        txn_type=payload.type,
        created_by=current_user.id,
        reason=payload.reason,
    )
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="inventory.adjusted",
        entity_type="product",
        entity_id=product.id,
        metadata={"type": payload.type.value, "quantity": payload.quantity, "reason": payload.reason},
    )
    db.commit()
    db.refresh(txn)
    return InventoryTransactionOut.model_validate(txn)


@router.get("/{product_id}/history", response_model=list[InventoryTransactionOut])
def inventory_history(
    product_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    txns = db.scalars(
        select(InventoryTransaction)
        .where(
            InventoryTransaction.business_id == current_user.business_id,
            InventoryTransaction.product_id == product_id,
        )
        .order_by(InventoryTransaction.created_at.desc())
    ).all()
    return [InventoryTransactionOut.model_validate(t) for t in txns]
