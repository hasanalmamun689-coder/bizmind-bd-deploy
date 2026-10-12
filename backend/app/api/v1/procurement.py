import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.procurement import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.schemas.procurement import PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderStatusUpdate
from app.services import audit

router = APIRouter(prefix="/api/purchase-orders", tags=["procurement"])

# section 16: only forward, sequential transitions are allowed. Nothing
# skips straight to ORDERED/DELIVERED, and nothing goes backwards except to
# CANCELLED — enforced server-side, not just hidden in the UI.
ALLOWED_TRANSITIONS = {
    PurchaseOrderStatus.DRAFT: {PurchaseOrderStatus.PENDING_APPROVAL, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.PENDING_APPROVAL: {PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.APPROVED: {PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.ORDERED: {PurchaseOrderStatus.DELIVERED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.DELIVERED: {PurchaseOrderStatus.COMPLETED},
    PurchaseOrderStatus.COMPLETED: set(),
    PurchaseOrderStatus.CANCELLED: set(),
}


@router.get("", response_model=list[PurchaseOrderOut])
def list_purchase_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.scalars(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.business_id == current_user.business_id)
        .order_by(PurchaseOrder.created_at.desc())
    ).all()
    return [PurchaseOrderOut.model_validate(o) for o in orders]


@router.post("", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None or supplier.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    order = PurchaseOrder(
        business_id=current_user.business_id,
        supplier_id=payload.supplier_id,
        created_by=current_user.id,
        expected_delivery_date=payload.expected_delivery_date,
        notes=payload.notes,
        status=PurchaseOrderStatus.DRAFT,
    )
    db.add(order)
    db.flush()

    total_cost = 0.0
    for item in payload.items:
        db.add(
            PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )
        total_cost += item.quantity * item.unit_price
    order.total_cost = total_cost
    db.flush()

    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="purchase_order.created",
        entity_type="purchase_order",
        entity_id=order.id,
        metadata={"total_cost": total_cost},
    )
    db.commit()
    db.refresh(order)
    return PurchaseOrderOut.model_validate(order)


def _get_owned_order(db: Session, business_id: uuid.UUID, order_id: uuid.UUID) -> PurchaseOrder:
    order = db.get(PurchaseOrder, order_id)
    if order is None or order.business_id != business_id:
        raise HTTPException(status_code=404, detail="Purchase order not found.")
    return order


@router.get("/{order_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    order = _get_owned_order(db, current_user.business_id, order_id)
    return PurchaseOrderOut.model_validate(order)


@router.put("/{order_id}/status", response_model=PurchaseOrderOut)
def update_purchase_order_status(
    order_id: uuid.UUID,
    payload: PurchaseOrderStatusUpdate,
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    order = _get_owned_order(db, current_user.business_id, order_id)
    if payload.status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move a purchase order from {order.status.value} to {payload.status.value}.",
        )
    order.status = payload.status
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="purchase_order.status_changed",
        entity_type="purchase_order",
        entity_id=order.id,
        metadata={"new_status": payload.status.value},
    )
    db.commit()
    db.refresh(order)
    return PurchaseOrderOut.model_validate(order)


@router.post("/{order_id}/approve", response_model=PurchaseOrderOut)
def approve_purchase_order(
    order_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.OWNER)),
    db: Session = Depends(get_db),
):
    """
    section 16/34: approving a real financial commitment is owner-only,
    regardless of who drafted it (manual or AI-recommended).
    """
    order = _get_owned_order(db, current_user.business_id, order_id)
    if order.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Only a pending-approval order can be approved.")
    order.status = PurchaseOrderStatus.APPROVED
    order.approved_by = current_user.id
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="purchase_order.approved",
        entity_type="purchase_order",
        entity_id=order.id,
    )
    db.commit()
    db.refresh(order)
    return PurchaseOrderOut.model_validate(order)
