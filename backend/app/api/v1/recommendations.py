import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.intelligence import Recommendation, RecommendationStatus
from app.models.procurement import (
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderSource, PurchaseOrderStatus,
)
from app.models.user import User, UserRole
from app.schemas.intelligence import RecommendationOut
from app.schemas.procurement import PurchaseOrderOut
from app.services import audit
from app.services.recommendations import generate_procurement_recommendations
from datetime import date, timedelta

router = APIRouter(prefix="/api/ai/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationOut])
def list_recommendations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Recommendation).where(Recommendation.business_id == current_user.business_id)
        .order_by(Recommendation.created_at.desc())
    ).all()
    return [RecommendationOut.model_validate(r) for r in rows]


@router.post("/generate", response_model=list[RecommendationOut])
def generate(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    created = generate_procurement_recommendations(db, current_user.business_id)
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="recommendations.generated", entity_type="recommendation",
                 metadata={"count": len(created)})
    db.commit()
    for r in created:
        db.refresh(r)
    return [RecommendationOut.model_validate(r) for r in created]


def _pending(db: Session, business_id: uuid.UUID, rec_id: uuid.UUID) -> Recommendation:
    rec = db.get(Recommendation, rec_id)
    if rec is None or rec.business_id != business_id:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if rec.status != RecommendationStatus.PENDING:
        raise HTTPException(status_code=400, detail="This recommendation has already been decided.")
    return rec


@router.post("/{rec_id}/approve", response_model=PurchaseOrderOut)
def approve(
    rec_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    """Human approval creates a purchase DRAFT only — never a placed order (sections 16, 25, 46)."""
    rec = _pending(db, current_user.business_id, rec_id)
    ev = rec.evidence
    if rec.type != "procurement" or "recommended_supplier" not in ev:
        raise HTTPException(status_code=400, detail="This recommendation cannot create a purchase draft.")
    supplier = ev["recommended_supplier"]
    order = PurchaseOrder(
        business_id=current_user.business_id,
        supplier_id=uuid.UUID(supplier["supplier_id"]),
        created_by=current_user.id,
        status=PurchaseOrderStatus.DRAFT,
        source=PurchaseOrderSource.AI_RECOMMENDATION,
        total_cost=ev["estimated_cost"],
        expected_delivery_date=date.today() + timedelta(days=supplier["delivery_days"]),
        notes=f"Created from AI recommendation {rec.id}",
    )
    db.add(order)
    db.flush()
    db.add(PurchaseOrderItem(
        purchase_order_id=order.id, product_id=uuid.UUID(ev["product_id"]),
        quantity=ev["suggested_quantity"], unit_price=supplier["price"],
    ))
    rec.status = RecommendationStatus.APPROVED
    rec.decided_by = current_user.id
    rec.related_purchase_order_id = order.id
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="recommendation.approved", entity_type="recommendation", entity_id=rec.id,
                 metadata={"purchase_order_id": str(order.id)})
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="purchase_draft.created", entity_type="purchase_order", entity_id=order.id)
    db.commit()
    db.refresh(order)
    return PurchaseOrderOut.model_validate(order)


@router.post("/{rec_id}/reject", response_model=RecommendationOut)
def reject(
    rec_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    rec = _pending(db, current_user.business_id, rec_id)
    rec.status = RecommendationStatus.REJECTED
    rec.decided_by = current_user.id
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="recommendation.rejected", entity_type="recommendation", entity_id=rec.id)
    db.commit()
    db.refresh(rec)
    return RecommendationOut.model_validate(rec)
