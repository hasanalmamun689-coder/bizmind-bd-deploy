"""
section 27: an optional, transparent health indicator. Every component is
shown alongside the overall score, and the methodology is documented as
changeable rather than presented as a universal scientific measure.
"""
import uuid

from sqlalchemy.orm import Session

from app.schemas.intelligence import BusinessHealthComponent, BusinessHealthScore
from app.services import analytics


def compute_business_health_score(db: Session, business_id: uuid.UUID) -> BusinessHealthScore:
    kpis = analytics.dashboard_kpis(db, business_id)
    inventory = analytics.inventory_analytics(db, business_id)
    suppliers = analytics.supplier_analytics(db, business_id)

    components: list[BusinessHealthComponent] = []

    # Profitability: estimated profit margin vs revenue.
    revenue = kpis["revenue"] or 1
    margin = (kpis["estimated_profit"] / revenue) * 100
    profitability_score = max(0, min(100, 50 + margin))
    components.append(
        BusinessHealthComponent(
            name="Profitability",
            score=round(profitability_score, 1),
            detail=f"Estimated profit margin of {round(margin, 1)}% on recorded revenue.",
        )
    )

    # Inventory efficiency: share of products in a healthy state.
    status_breakdown = inventory["status_breakdown"]
    total_products = sum(status_breakdown.values()) or 1
    healthy = status_breakdown.get("healthy", 0)
    inventory_score = (healthy / total_products) * 100
    components.append(
        BusinessHealthComponent(
            name="Inventory efficiency",
            score=round(inventory_score, 1),
            detail=f"{healthy} of {total_products} active products are at a healthy stock level.",
        )
    )

    # Supplier performance: average reliability score.
    if suppliers:
        avg_reliability = sum(s["reliability_score"] for s in suppliers) / len(suppliers)
    else:
        avg_reliability = 70.0
    components.append(
        BusinessHealthComponent(
            name="Supplier performance",
            score=round(avg_reliability, 1),
            detail=f"Average supplier reliability score across {len(suppliers)} supplier(s).",
        )
    )

    # Expense control: expenses as a share of revenue (lower is better).
    expense_ratio = (kpis["total_expenses"] / revenue) * 100
    expense_score = max(0, min(100, 100 - expense_ratio))
    components.append(
        BusinessHealthComponent(
            name="Expense control",
            score=round(expense_score, 1),
            detail=f"Recorded expenses are {round(expense_ratio, 1)}% of recorded revenue.",
        )
    )

    overall = round(sum(c.score for c in components) / len(components), 1)

    return BusinessHealthScore(overall_score=overall, components=components)
