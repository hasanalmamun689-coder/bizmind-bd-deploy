"""
section 22/23: THE controlled tool layer. The AI never gets raw SQL or an
ORM session — it can only call the named functions below, each of which
returns a small, structured, already-computed result built from the same
analytics/forecasting/risk services the rest of the app uses.

Every tool function takes (db, business_id, **params) and returns a plain
JSON-serializable dict. Adding a new capability for the AI means adding a
function here and to TOOL_SPECS — never widening its database access.
"""
import uuid
from datetime import date, datetime, timedelta
from app.core.clock import utcnow

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Product
from app.models.expense import Expense
from app.models.procurement import PurchaseOrder, PurchaseOrderItem
from app.models.sales import Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier, SupplierProduct
from app.services import analytics, forecasting
from app.services.risk import detect_business_risks


def get_sales_summary(db: Session, business_id: uuid.UUID, days: int = 30) -> dict:
    trend = analytics.sales_trend(db, business_id, days=days)
    total_revenue = sum(row["revenue"] for row in trend)
    total_orders = sum(row["orders"] for row in trend)
    return {
        "period_days": days,
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "average_order_value": round(total_revenue / total_orders, 2) if total_orders else 0,
        "daily_trend": trend,
    }


def get_product_sales(db: Session, business_id: uuid.UUID, limit: int = 10) -> dict:
    return {"top_products": analytics.top_products(db, business_id, limit=limit)}


def get_inventory_status(db: Session, business_id: uuid.UUID) -> dict:
    return analytics.inventory_analytics(db, business_id)


def get_low_stock_products(db: Session, business_id: uuid.UUID) -> dict:
    from app.models.catalog import ProductStatus

    rows = db.scalars(
        select(Product).where(
            Product.business_id == business_id,
            Product.is_active.is_(True),
            Product.status.in_(
                [ProductStatus.LOW_STOCK, ProductStatus.CRITICAL, ProductStatus.OUT_OF_STOCK]
            ),
        )
    ).all()
    return {
        "low_stock_products": [
            {
                "product_id": str(p.id),
                "name": p.name,
                "sku": p.sku,
                "current_stock": p.current_stock,
                "minimum_stock": p.minimum_stock,
                "status": p.status.value,
            }
            for p in rows
        ]
    }


def get_inventory_history(db: Session, business_id: uuid.UUID, product_id: str, days: int = 30) -> dict:
    from app.models.inventory import InventoryTransaction

    since = utcnow() - timedelta(days=days)
    rows = db.scalars(
        select(InventoryTransaction)
        .where(
            InventoryTransaction.business_id == business_id,
            InventoryTransaction.product_id == uuid.UUID(product_id),
            InventoryTransaction.created_at >= since,
        )
        .order_by(InventoryTransaction.created_at)
    ).all()
    return {
        "transactions": [
            {
                "type": t.type.value,
                "quantity_delta": t.quantity_delta,
                "resulting_stock": t.resulting_stock,
                "date": t.created_at.isoformat(),
            }
            for t in rows
        ]
    }


def get_supplier_prices(db: Session, business_id: uuid.UUID, product_id: str | None = None) -> dict:
    query = (
        select(Supplier.name, SupplierProduct.price, SupplierProduct.minimum_order_quantity, Product.name)
        .join(SupplierProduct, SupplierProduct.supplier_id == Supplier.id)
        .join(Product, Product.id == SupplierProduct.product_id)
        .where(Supplier.business_id == business_id)
    )
    if product_id:
        query = query.where(SupplierProduct.product_id == uuid.UUID(product_id))
    rows = db.execute(query).all()
    return {
        "supplier_prices": [
            {"supplier": s, "product": p, "price": float(price), "moq": moq}
            for s, price, moq, p in rows
        ]
    }


def get_supplier_performance(db: Session, business_id: uuid.UUID) -> dict:
    return {"suppliers": analytics.supplier_analytics(db, business_id)}


def get_purchase_history(db: Session, business_id: uuid.UUID, limit: int = 20) -> dict:
    rows = db.scalars(
        select(PurchaseOrder)
        .where(PurchaseOrder.business_id == business_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(limit)
    ).all()
    return {
        "purchase_orders": [
            {
                "id": str(po.id),
                "supplier_id": str(po.supplier_id),
                "status": po.status.value,
                "total_cost": float(po.total_cost),
                "created_at": po.created_at.isoformat(),
            }
            for po in rows
        ]
    }


def forecast_product_demand(db: Session, business_id: uuid.UUID, product_id: str, horizon_days: int = 14) -> dict:
    product = db.get(Product, uuid.UUID(product_id))
    if product is None or product.business_id != business_id:
        return {"error": "product not found"}
    forecast = forecasting.generate_forecast(db, business_id, product, horizon_days)
    return {
        "product_id": str(product.id),
        "product_name": product.name,
        "horizon_days": horizon_days,
        "model_used": forecast.model_used,
        "predicted_demand": float(forecast.predicted_demand),
        "current_stock": forecast.current_stock_at_run,
        "estimated_stockout_date": (
            forecast.estimated_stockout_date.isoformat() if forecast.estimated_stockout_date else None
        ),
        "risk_level": forecast.risk_level.value,
        "insufficient_data": forecast.insufficient_data,
    }


def calculate_profit(db: Session, business_id: uuid.UUID, days: int = 30) -> dict:
    return analytics.profit_breakdown(db, business_id, days=days)


def get_expense_breakdown(db: Session, business_id: uuid.UUID, days: int = 30) -> dict:
    since = (utcnow() - timedelta(days=days)).date()
    rows = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(Expense.business_id == business_id, Expense.expense_date >= since)
        .group_by(Expense.category)
    ).all()
    return {
        "period_days": days,
        "by_category": {cat.value: float(total) for cat, total in rows},
    }


def detect_anomalies(db: Session, business_id: uuid.UUID) -> dict:
    return get_business_risks(db, business_id)


def get_business_risks(db: Session, business_id: uuid.UUID) -> dict:
    risks = detect_business_risks(db, business_id)
    return {"risks": [r.model_dump() for r in risks]}


def get_customer_summary(db: Session, business_id: uuid.UUID) -> dict:
    from app.models.customer import Customer

    customers = db.scalars(select(Customer).where(Customer.business_id == business_id)).all()
    summaries = []
    for c in customers:
        s = analytics.customer_summary(db, business_id, c)
        summaries.append({"customer_id": str(c.id), "name": c.name, **s})
    return {"customers": summaries}


TOOL_REGISTRY = {
    "get_sales_summary": get_sales_summary,
    "get_product_sales": get_product_sales,
    "get_inventory_status": get_inventory_status,
    "get_low_stock_products": get_low_stock_products,
    "get_inventory_history": get_inventory_history,
    "get_supplier_prices": get_supplier_prices,
    "get_supplier_performance": get_supplier_performance,
    "get_purchase_history": get_purchase_history,
    "forecast_product_demand": forecast_product_demand,
    "calculate_profit": calculate_profit,
    "get_expense_breakdown": get_expense_breakdown,
    "detect_anomalies": detect_anomalies,
    "get_business_risks": get_business_risks,
    "get_customer_summary": get_customer_summary,
}

# JSON-schema tool specs handed to whichever LLM provider is configured.
# `create_purchase_draft` is intentionally NOT a read tool here — it is only
# ever invoked through the recommendation-approval API endpoint, which is
# gated by require_role(OWNER) (section 16/25: AI must never place an order).
TOOL_SPECS = [
    {
        "name": "get_sales_summary",
        "description": "Get total revenue, orders and daily trend for the last N days.",
        "parameters": {"days": "integer, optional, default 30"},
    },
    {
        "name": "get_product_sales",
        "description": "Get the best-selling products by units sold.",
        "parameters": {"limit": "integer, optional, default 10"},
    },
    {
        "name": "get_inventory_status",
        "description": "Get inventory value, status breakdown and dead stock.",
        "parameters": {},
    },
    {
        "name": "get_low_stock_products",
        "description": "List products that are low stock, critical, or out of stock.",
        "parameters": {},
    },
    {
        "name": "get_supplier_prices",
        "description": "Get supplier prices for a product (or all products).",
        "parameters": {"product_id": "uuid string, optional"},
    },
    {
        "name": "get_supplier_performance",
        "description": "Get reliability, quality and fulfillment metrics for all suppliers.",
        "parameters": {},
    },
    {
        "name": "get_purchase_history",
        "description": "Get recent purchase orders.",
        "parameters": {"limit": "integer, optional, default 20"},
    },
    {
        "name": "forecast_product_demand",
        "description": "Forecast demand for a product over a horizon and estimate stockout risk.",
        "parameters": {"product_id": "uuid string, required", "horizon_days": "integer, optional, default 14"},
    },
    {
        "name": "calculate_profit",
        "description": "Get revenue, cost of goods, gross profit and estimated profit for a period.",
        "parameters": {"days": "integer, optional, default 30"},
    },
    {
        "name": "get_expense_breakdown",
        "description": "Get expenses grouped by category for a period.",
        "parameters": {"days": "integer, optional, default 30"},
    },
    {
        "name": "get_business_risks",
        "description": "Get detected business risks: sales decline, expense spikes, profit decline, supplier issues.",
        "parameters": {},
    },
    {
        "name": "get_customer_summary",
        "description": "Get per-customer order count, spend and segment.",
        "parameters": {},
    },
]
