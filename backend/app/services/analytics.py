"""section 10/18: real, database-backed analytics — no decorative fake charts."""
import uuid
from datetime import datetime, timedelta
from app.core.clock import utcnow

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductStatus
from app.models.customer import Customer
from app.models.expense import Expense
from app.models.intelligence import Alert, AlertStatus
from app.models.procurement import PurchaseOrder, PurchaseOrderStatus
from app.models.sales import Sale, SaleItem, SaleStatus


def dashboard_kpis(db: Session, business_id: uuid.UUID) -> dict:
    total_sales = db.scalar(
        select(func.count(Sale.id)).where(Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED)
    ) or 0
    revenue = db.scalar(
        select(func.coalesce(func.sum(Sale.total_amount), 0)).where(
            Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED
        )
    ) or 0
    cost = db.scalar(
        select(func.coalesce(func.sum(Sale.total_cost), 0)).where(
            Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED
        )
    ) or 0
    total_expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.business_id == business_id)
    ) or 0
    inventory_value = db.scalar(
        select(func.coalesce(func.sum(Product.current_stock * Product.purchase_price), 0)).where(
            Product.business_id == business_id, Product.is_active.is_(True)
        )
    ) or 0
    low_stock_items = db.scalar(
        select(func.count(Product.id)).where(
            Product.business_id == business_id,
            Product.status.in_([ProductStatus.LOW_STOCK, ProductStatus.CRITICAL, ProductStatus.OUT_OF_STOCK]),
        )
    ) or 0
    pending_purchases = db.scalar(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.business_id == business_id,
            PurchaseOrder.status.in_([PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING_APPROVAL]),
        )
    ) or 0
    active_customers = db.scalar(
        select(func.count(func.distinct(Sale.customer_id))).where(
            Sale.business_id == business_id,
            Sale.created_at >= utcnow() - timedelta(days=90),
            Sale.customer_id.is_not(None),
        )
    ) or 0

    estimated_profit = float(revenue) - float(cost) - float(total_expenses)

    return {
        "total_sales": total_sales,
        "revenue": float(revenue),
        "cost_of_goods_sold": float(cost),
        "gross_profit": float(revenue) - float(cost),
        "total_expenses": float(total_expenses),
        "estimated_profit": estimated_profit,
        "inventory_value": float(inventory_value),
        "low_stock_items": low_stock_items,
        "pending_purchases": pending_purchases,
        "active_customers": active_customers,
    }


def sales_trend(db: Session, business_id: uuid.UUID, days: int = 30) -> list[dict]:
    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(func.date(Sale.created_at), func.sum(Sale.total_amount), func.count(Sale.id))
        .where(Sale.business_id == business_id, Sale.created_at >= since, Sale.status == SaleStatus.COMPLETED)
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at))
    ).all()
    return [{"date": str(d), "revenue": float(r or 0), "orders": c} for d, r, c in rows]


def top_products(db: Session, business_id: uuid.UUID, limit: int = 10) -> list[dict]:
    rows = db.execute(
        select(
            Product.id,
            Product.name,
            func.sum(SaleItem.quantity).label("units_sold"),
            func.sum(SaleItem.quantity * SaleItem.unit_price).label("revenue"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(limit)
    ).all()
    return [
        {"product_id": str(pid), "name": name, "units_sold": int(units), "revenue": float(rev or 0)}
        for pid, name, units, rev in rows
    ]


def profit_breakdown(db: Session, business_id: uuid.UUID, days: int = 30) -> dict:
    since = utcnow() - timedelta(days=days)
    revenue = db.scalar(
        select(func.coalesce(func.sum(Sale.total_amount), 0)).where(
            Sale.business_id == business_id, Sale.created_at >= since, Sale.status == SaleStatus.COMPLETED
        )
    ) or 0
    cogs = db.scalar(
        select(func.coalesce(func.sum(Sale.total_cost), 0)).where(
            Sale.business_id == business_id, Sale.created_at >= since, Sale.status == SaleStatus.COMPLETED
        )
    ) or 0
    expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.business_id == business_id, Expense.expense_date >= since.date()
        )
    ) or 0
    gross_profit = float(revenue) - float(cogs)
    estimated_profit = gross_profit - float(expenses)
    margin = (gross_profit / float(revenue) * 100) if revenue else 0

    return {
        "period_days": days,
        "revenue": float(revenue),
        "cost_of_goods_sold": float(cogs),
        "gross_profit": gross_profit,
        "gross_margin_percent": round(margin, 2),
        "operating_expenses": float(expenses),
        "estimated_profit": estimated_profit,
    }


def inventory_analytics(db: Session, business_id: uuid.UUID) -> dict:
    products = db.scalars(
        select(Product).where(Product.business_id == business_id, Product.is_active.is_(True))
    ).all()

    by_status: dict[str, int] = {}
    total_value = 0.0
    dead_stock = []
    for p in products:
        by_status[p.status.value] = by_status.get(p.status.value, 0) + 1
        total_value += p.current_stock * float(p.purchase_price)

    # Dead stock: no sale in the last 60 days but stock > 0
    since = utcnow() - timedelta(days=60)
    sold_recently = set(
        db.scalars(
            select(SaleItem.product_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.business_id == business_id, Sale.created_at >= since, Sale.status == SaleStatus.COMPLETED)
            .distinct()
        ).all()
    )
    for p in products:
        if p.current_stock > 0 and p.id not in sold_recently:
            dead_stock.append({"product_id": str(p.id), "name": p.name, "current_stock": p.current_stock})

    return {
        "total_inventory_value": round(total_value, 2),
        "status_breakdown": by_status,
        "dead_stock": dead_stock,
    }


def supplier_analytics(db: Session, business_id: uuid.UUID) -> list[dict]:
    from app.models.supplier import Supplier

    suppliers = db.scalars(select(Supplier).where(Supplier.business_id == business_id)).all()
    result = []
    for s in suppliers:
        order_count = db.scalar(
            select(func.count(PurchaseOrder.id)).where(PurchaseOrder.supplier_id == s.id)
        ) or 0
        result.append(
            {
                "supplier_id": str(s.id),
                "name": s.name,
                "reliability_score": float(s.reliability_score),
                "quality_score": float(s.quality_score),
                "fulfillment_rate": float(s.fulfillment_rate),
                "delivery_time_days": s.delivery_time_days,
                "order_count": order_count,
            }
        )
    return result


def customer_summary(db: Session, business_id: uuid.UUID, customer: Customer) -> dict:
    rows = db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.total_amount), 0), func.max(Sale.created_at)).where(
            Sale.business_id == business_id, Sale.customer_id == customer.id, Sale.status == SaleStatus.COMPLETED
        )
    ).one()
    total_orders, total_spent, last_purchase_at = rows

    if total_orders == 0:
        segment = "new"
    elif last_purchase_at and last_purchase_at < utcnow() - timedelta(days=90):
        segment = "inactive"
    elif float(total_spent) > 50000:
        segment = "high-value"
    else:
        segment = "regular"

    return {
        "total_orders": total_orders,
        "total_spent": float(total_spent),
        "last_purchase_at": last_purchase_at,
        "segment": segment,
    }


def unresolved_alert_count(db: Session, business_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count(Alert.id)).where(
            Alert.business_id == business_id, Alert.status.in_([AlertStatus.UNREAD, AlertStatus.READ])
        )
    ) or 0


def monthly_financials(db: Session, business_id: uuid.UUID, months: int = 6) -> list[dict]:
    """Per-month revenue, COGS, gross profit, expenses and estimated profit (real rows only)."""
    from app.models.catalog import Category  # noqa: F401  (kept local to avoid import cycles)

    sales = db.execute(
        select(func.to_char(Sale.created_at, "YYYY-MM"), func.sum(Sale.total_amount), func.sum(Sale.total_cost))
        .where(Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED)
        .group_by(func.to_char(Sale.created_at, "YYYY-MM"))
    ).all()
    exps = db.execute(
        select(func.to_char(Expense.expense_date, "YYYY-MM"), func.sum(Expense.amount))
        .where(Expense.business_id == business_id)
        .group_by(func.to_char(Expense.expense_date, "YYYY-MM"))
    ).all()
    by_month: dict[str, dict] = {}
    for m, rev, cogs in sales:
        by_month.setdefault(m, {"revenue": 0.0, "cogs": 0.0, "expenses": 0.0})
        by_month[m]["revenue"], by_month[m]["cogs"] = float(rev or 0), float(cogs or 0)
    for m, amt in exps:
        by_month.setdefault(m, {"revenue": 0.0, "cogs": 0.0, "expenses": 0.0})
        by_month[m]["expenses"] = float(amt or 0)
    out = []
    for m in sorted(by_month)[-months:]:
        v = by_month[m]
        out.append({"month": m, "revenue": v["revenue"], "cost_of_goods_sold": v["cogs"],
                    "gross_profit": v["revenue"] - v["cogs"], "expenses": v["expenses"],
                    "estimated_profit": v["revenue"] - v["cogs"] - v["expenses"]})
    return out


def category_performance(db: Session, business_id: uuid.UUID, days: int = 30) -> list[dict]:
    from app.models.catalog import Category

    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(func.coalesce(Category.name, "Uncategorized"),
               func.sum(SaleItem.quantity * SaleItem.unit_price),
               func.sum(SaleItem.quantity * (SaleItem.unit_price - SaleItem.unit_cost)),
               func.sum(SaleItem.quantity))
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Sale.business_id == business_id, Sale.status == SaleStatus.COMPLETED, Sale.created_at >= since)
        .group_by(func.coalesce(Category.name, "Uncategorized"))
        .order_by(func.sum(SaleItem.quantity * SaleItem.unit_price).desc())
    ).all()
    return [{"category": c, "revenue": float(r or 0), "gross_profit": float(g or 0), "units": int(u or 0)} for c, r, g, u in rows]


def inventory_movement(db: Session, business_id: uuid.UUID, days: int = 30) -> list[dict]:
    from app.models.inventory import InventoryTransaction

    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(func.date(InventoryTransaction.created_at),
               func.coalesce(func.sum(InventoryTransaction.quantity_delta).filter(InventoryTransaction.quantity_delta > 0), 0),
               func.coalesce(-func.sum(InventoryTransaction.quantity_delta).filter(InventoryTransaction.quantity_delta < 0), 0))
        .where(InventoryTransaction.business_id == business_id, InventoryTransaction.created_at >= since)
        .group_by(func.date(InventoryTransaction.created_at)).order_by(func.date(InventoryTransaction.created_at))
    ).all()
    return [{"date": str(d), "stock_in": int(i), "stock_out": int(o)} for d, i, o in rows]
