"""
section 25: recommendation pipeline
Analytics -> Forecast -> Risk -> Recommendation (evidence + reasoning) -> human approval -> purchase DRAFT.
Every number in `evidence` comes from the forecasting/supplier tables; nothing is invented.
"""
import math
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Product
from app.models.intelligence import Recommendation, RecommendationStatus, RiskLevel
from app.models.supplier import Supplier, SupplierProduct
from app.services import forecasting

COVER_DAYS = 30  # target days of demand to stock up to


def _best_supplier(db: Session, business_id: uuid.UUID, product: Product):
    rows = db.execute(
        select(Supplier, SupplierProduct)
        .join(SupplierProduct, SupplierProduct.supplier_id == Supplier.id)
        .where(Supplier.business_id == business_id, SupplierProduct.product_id == product.id)
    ).all()
    if not rows:
        return None, []
    candidates = [
        {
            "supplier_id": str(s.id),
            "supplier": s.name,
            "price": float(sp.price),
            "moq": sp.minimum_order_quantity,
            "delivery_days": s.delivery_time_days,
            "reliability": float(s.reliability_score),
            "fulfillment_rate": float(s.fulfillment_rate),
        }
        for s, sp in rows
    ]
    # Transparent ranking: reliable suppliers first among those within 10% of the cheapest price.
    cheapest = min(c["price"] for c in candidates)
    shortlisted = [c for c in candidates if c["price"] <= cheapest * 1.10]
    best = sorted(shortlisted, key=lambda c: (-c["reliability"], c["price"]))[0]
    return best, candidates


def generate_procurement_recommendations(db: Session, business_id: uuid.UUID) -> list[Recommendation]:
    products = db.scalars(
        select(Product).where(Product.business_id == business_id, Product.is_active.is_(True))
    ).all()
    existing_pending = {
        r.evidence.get("product_id")
        for r in db.scalars(
            select(Recommendation).where(
                Recommendation.business_id == business_id,
                Recommendation.type == "procurement",
                Recommendation.status == RecommendationStatus.PENDING,
            )
        ).all()
    }
    created: list[Recommendation] = []
    for p in products:
        if str(p.id) in existing_pending:
            continue
        fc = forecasting.generate_forecast(db, business_id, p, 14)
        if fc.insufficient_data or fc.risk_level not in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            continue
        daily = float(fc.predicted_demand) / 14
        target = math.ceil(daily * COVER_DAYS)
        best, candidates = _best_supplier(db, business_id, p)
        if best is None:
            continue
        qty = max(target - p.current_stock, best["moq"])
        est_cost = round(qty * best["price"], 2)
        days_left = round(p.current_stock / daily, 1) if daily else None
        rec = Recommendation(
            business_id=business_id,
            type="procurement",
            title=f"Reorder {p.name}",
            evidence={
                "product_id": str(p.id),
                "product": p.name,
                "current_stock": p.current_stock,
                "avg_daily_demand": round(daily, 2),
                "estimated_days_of_stock": days_left,
                "forecast_model": fc.model_used,
                "risk_level": fc.risk_level.value,
                "suggested_quantity": qty,
                "recommended_supplier": best,
                "supplier_options": candidates,
                "estimated_cost": est_cost,
            },
            reasoning=(
                f"Forecast (exponential smoothing) expects ~{round(daily, 1)} units/day; "
                f"current stock covers about {days_left} days, giving {fc.risk_level.value} stockout risk. "
                f"Ordering {qty} units restores ~{COVER_DAYS} days of cover. "
                f"{best['supplier']} was chosen as the most reliable supplier within 10% of the lowest price. "
                "This is an estimate, not a guarantee."
            ),
            suggested_action=f"Review and approve to create a purchase draft of {qty} units from {best['supplier']}.",
        )
        db.add(rec)
        created.append(rec)
    db.flush()
    return created
