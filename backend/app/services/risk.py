"""
section 21: anomaly/risk detection. Every risk returned states its own
evidence and, if there isn't enough data, says so explicitly rather than
inventing a conclusion (section 46).
"""
import uuid
from datetime import datetime, timedelta
from app.core.clock import utcnow

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.intelligence import AlertSeverity
from app.models.sales import Sale, SaleStatus
from app.models.catalog import Product, ProductStatus
from app.models.supplier import Supplier, SupplierPriceHistory
from app.schemas.intelligence import RiskOut

RECENT_WINDOW_DAYS = 30
PRIOR_WINDOW_DAYS = 30


def _period_revenue(db: Session, business_id: uuid.UUID, start: datetime, end: datetime) -> float:
    return float(
        db.scalar(
            select(func.coalesce(func.sum(Sale.total_amount), 0)).where(
                Sale.business_id == business_id,
                Sale.status == SaleStatus.COMPLETED,
                Sale.created_at >= start,
                Sale.created_at < end,
            )
        )
        or 0
    )


def _period_expenses(db: Session, business_id: uuid.UUID, start, end) -> float:
    return float(
        db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.business_id == business_id,
                Expense.expense_date >= start,
                Expense.expense_date < end,
            )
        )
        or 0
    )


def detect_business_risks(db: Session, business_id: uuid.UUID) -> list[RiskOut]:
    now = utcnow()
    recent_start = now - timedelta(days=RECENT_WINDOW_DAYS)
    prior_start = recent_start - timedelta(days=PRIOR_WINDOW_DAYS)

    risks: list[RiskOut] = []

    # --- Sales decline ---
    recent_revenue = _period_revenue(db, business_id, recent_start, now)
    prior_revenue = _period_revenue(db, business_id, prior_start, recent_start)
    if prior_revenue == 0 and recent_revenue == 0:
        risks.append(
            RiskOut(
                risk="Insufficient sales history",
                severity=AlertSeverity.INFO,
                evidence={"recent_revenue": recent_revenue, "prior_revenue": prior_revenue},
                explanation="Not enough sales data exists yet to evaluate a sales trend.",
                recommended_investigation="Record sales for a few more weeks before trusting this signal.",
            )
        )
    elif prior_revenue > 0:
        change_pct = ((recent_revenue - prior_revenue) / prior_revenue) * 100
        if change_pct <= -20:
            risks.append(
                RiskOut(
                    risk="Sales decline",
                    severity=AlertSeverity.CRITICAL if change_pct <= -40 else AlertSeverity.WARNING,
                    evidence={
                        "recent_30d_revenue": recent_revenue,
                        "prior_30d_revenue": prior_revenue,
                        "change_percent": round(change_pct, 1),
                    },
                    explanation=(
                        f"Revenue over the last {RECENT_WINDOW_DAYS} days is "
                        f"{abs(round(change_pct, 1))}% lower than the previous period."
                    ),
                    recommended_investigation="Check which products or customer segments dropped off.",
                )
            )

    # --- Expense spike ---
    recent_expenses = _period_expenses(db, business_id, recent_start.date(), now.date())
    prior_expenses = _period_expenses(db, business_id, prior_start.date(), recent_start.date())
    if prior_expenses > 0:
        exp_change_pct = ((recent_expenses - prior_expenses) / prior_expenses) * 100
        if exp_change_pct >= 25:
            risks.append(
                RiskOut(
                    risk="Expense spike",
                    severity=AlertSeverity.WARNING if exp_change_pct < 50 else AlertSeverity.CRITICAL,
                    evidence={
                        "recent_30d_expenses": recent_expenses,
                        "prior_30d_expenses": prior_expenses,
                        "change_percent": round(exp_change_pct, 1),
                    },
                    explanation=f"Expenses rose {round(exp_change_pct, 1)}% versus the prior period.",
                    recommended_investigation="Review the expense breakdown by category for the spike source.",
                )
            )

    # --- Profit decline ---
    recent_cost = float(
        db.scalar(
            select(func.coalesce(func.sum(Sale.total_cost), 0)).where(
                Sale.business_id == business_id, Sale.created_at >= recent_start, Sale.status == SaleStatus.COMPLETED
            )
        )
        or 0
    )
    recent_profit = recent_revenue - recent_cost - recent_expenses
    prior_cost = float(
        db.scalar(
            select(func.coalesce(func.sum(Sale.total_cost), 0)).where(
                Sale.business_id == business_id,
                Sale.created_at >= prior_start,
                Sale.created_at < recent_start,
                Sale.status == SaleStatus.COMPLETED,
            )
        )
        or 0
    )
    prior_profit = prior_revenue - prior_cost - prior_expenses
    if prior_profit > 0 and recent_profit < prior_profit * 0.8:
        risks.append(
            RiskOut(
                risk="Profit decline",
                severity=AlertSeverity.WARNING,
                evidence={"recent_estimated_profit": recent_profit, "prior_estimated_profit": prior_profit},
                explanation="Estimated profit fell more than 20% versus the prior 30-day period.",
                recommended_investigation="Compare revenue, cost of goods and expense trends for the same window.",
            )
        )

    # --- Supplier reliability ---
    unreliable_suppliers = db.scalars(
        select(Supplier).where(Supplier.business_id == business_id, Supplier.reliability_score < 60)
    ).all()
    for s in unreliable_suppliers:
        risks.append(
            RiskOut(
                risk=f"Low supplier reliability: {s.name}",
                severity=AlertSeverity.WARNING,
                evidence={"supplier_id": str(s.id), "reliability_score": float(s.reliability_score)},
                explanation=f"{s.name} has a reliability score of {s.reliability_score}, below the 60 threshold.",
                recommended_investigation="Compare against alternative suppliers for the same products.",
            )
        )


    # --- Supplier price increases (needs real price history) ---
    since_90 = now - timedelta(days=90)
    history = db.execute(
        select(SupplierPriceHistory, Supplier.name, Product.name)
        .join(Supplier, Supplier.id == SupplierPriceHistory.supplier_id)
        .join(Product, Product.id == SupplierPriceHistory.product_id)
        .where(Supplier.business_id == business_id, SupplierPriceHistory.created_at >= since_90)
        .order_by(SupplierPriceHistory.created_at)
    ).all()
    series: dict[tuple, list] = {}
    for h, sname, pname in history:
        series.setdefault((h.supplier_id, h.product_id, sname, pname), []).append(float(h.price))
    for (_, _, sname, pname), prices in series.items():
        if len(prices) >= 2 and prices[0] > 0:
            change = (prices[-1] - prices[0]) / prices[0] * 100
            if change >= 10:
                risks.append(
                    RiskOut(
                        risk=f"Supplier price increase: {pname} from {sname}",
                        severity=AlertSeverity.WARNING,
                        evidence={"first_price_90d": prices[0], "latest_price": prices[-1], "change_percent": round(change, 1)},
                        explanation=f"{sname}'s price for {pname} rose {round(change, 1)}% within 90 days, which squeezes margin.",
                        recommended_investigation="Compare alternative suppliers or renegotiate; check whether the selling price still covers cost.",
                    )
                )

    # --- Dead stock and overstock (capital tied up) ---
    from app.services.analytics import inventory_analytics

    inv = inventory_analytics(db, business_id)
    if inv["dead_stock"]:
        top = sorted(inv["dead_stock"], key=lambda d: -d["current_stock"])[:5]
        risks.append(
            RiskOut(
                risk="Dead stock",
                severity=AlertSeverity.WARNING,
                evidence={"dead_stock_products": len(inv["dead_stock"]), "largest": [f"{d['name']} ({d['current_stock']})" for d in top]},
                explanation=f"{len(inv['dead_stock'])} product(s) hold stock but have had no completed sale in 60 days.",
                recommended_investigation="Consider discounts or bundles, and stop reordering these products.",
            )
        )
    over = db.scalars(
        select(Product).where(Product.business_id == business_id, Product.is_active.is_(True),
                              Product.status == ProductStatus.OVERSTOCK)
    ).all()
    if over:
        risks.append(
            RiskOut(
                risk="Overstock",
                severity=AlertSeverity.INFO,
                evidence={"overstocked_products": len(over), "examples": [f"{p.name} ({p.current_stock} > max {p.maximum_stock})" for p in over[:5]]},
                explanation=f"{len(over)} product(s) exceed their maximum stock level, tying up cash.",
                recommended_investigation="Pause reorders and review the maximum stock thresholds.",
            )
        )

    # --- Rapid inventory depletion (last 7 days vs the previous 21) ---
    from app.models.sales import SaleItem

    def _units(start, end):
        rows = db.execute(
            select(SaleItem.product_id, func.sum(SaleItem.quantity))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED,
                   Sale.created_at >= start, Sale.created_at < end)
            .group_by(SaleItem.product_id)
        ).all()
        return {pid: int(q) for pid, q in rows}

    last7 = _units(now - timedelta(days=7), now)
    prev21 = _units(now - timedelta(days=28), now - timedelta(days=7))
    for pid, q7 in last7.items():
        base = prev21.get(pid, 0) / 3.0  # average per 7 days
        if base >= 10 and q7 >= base * 2:
            product = db.get(Product, pid)
            if product and product.is_active:
                risks.append(
                    RiskOut(
                        risk=f"Rapid depletion: {product.name}",
                        severity=AlertSeverity.WARNING,
                        evidence={"units_last_7d": q7, "typical_weekly_units": round(base, 1), "current_stock": product.current_stock},
                        explanation=f"{product.name} sold {q7} units in 7 days versus a typical ~{round(base)} per week; stock is {product.current_stock}.",
                        recommended_investigation="Confirm whether demand is a temporary spike, then check supplier lead time before stock runs out.",
                    )
                )

    if not risks:
        risks.append(
            RiskOut(
                risk="No significant risks detected",
                severity=AlertSeverity.INFO,
                evidence={},
                explanation="Current sales, expense, profit and supplier signals are within normal ranges.",
                recommended_investigation="No action needed at this time.",
            )
        )

    return risks
