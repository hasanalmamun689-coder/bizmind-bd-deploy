"""
section 19: forecasting starts simple and stays transparent.

Model: exponential smoothing over daily units sold in the last 90 days,
compared against current stock to estimate a stockout date. If there is not
enough sales history, the forecast is explicitly marked `insufficient_data`
rather than fabricated (section 21/46).
"""
import uuid
from datetime import date, datetime, timedelta
from app.core.clock import utcnow

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Product
from app.models.intelligence import Forecast, RiskLevel
from app.models.sales import Sale, SaleItem, SaleStatus

MIN_DAYS_OF_HISTORY = 7
SMOOTHING_ALPHA = 0.3


def _daily_units_sold(db: Session, business_id: uuid.UUID, product_id: uuid.UUID, days: int = 90) -> list[float]:
    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(Sale.created_at, SaleItem.quantity)
        .join(SaleItem, SaleItem.sale_id == Sale.id)
        .where(
            Sale.business_id == business_id,
            SaleItem.product_id == product_id,
            Sale.created_at >= since,
            Sale.status == SaleStatus.COMPLETED,
        )
    ).all()

    if not rows:
        return []

    by_day: dict[date, int] = {}
    for created_at, quantity in rows:
        d = created_at.date()
        by_day[d] = by_day.get(d, 0) + quantity

    if not by_day:
        return []

    start = min(by_day.keys())
    end = max(by_day.keys())
    series = []
    current = start
    while current <= end:
        series.append(float(by_day.get(current, 0)))
        current += timedelta(days=1)
    return series


def _exponential_smoothing_forecast(series: list[float], horizon_days: int) -> float:
    if not series:
        return 0.0
    level = series[0]
    for value in series[1:]:
        level = SMOOTHING_ALPHA * value + (1 - SMOOTHING_ALPHA) * level
    return round(level * horizon_days, 2)


def generate_forecast(
    db: Session, business_id: uuid.UUID, product: Product, horizon_days: int
) -> Forecast:
    series = _daily_units_sold(db, business_id, product.id)

    if len(series) < MIN_DAYS_OF_HISTORY:
        forecast = Forecast(
            business_id=business_id,
            product_id=product.id,
            horizon_days=horizon_days,
            model_used="exponential_smoothing",
            predicted_demand=0,
            current_stock_at_run=product.current_stock,
            estimated_stockout_date=None,
            risk_level=RiskLevel.LOW,
            insufficient_data=True,
        )
        db.add(forecast)
        db.flush()
        return forecast

    predicted_demand = _exponential_smoothing_forecast(series, horizon_days)
    avg_daily_demand = predicted_demand / horizon_days if horizon_days else 0

    estimated_stockout_date = None
    if avg_daily_demand > 0:
        days_of_cover = product.current_stock / avg_daily_demand
        estimated_stockout_date = (utcnow() + timedelta(days=days_of_cover)).date()
        if days_of_cover <= 3:
            risk_level = RiskLevel.CRITICAL
        elif days_of_cover <= 7:
            risk_level = RiskLevel.HIGH
        elif days_of_cover <= 14:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW
    else:
        risk_level = RiskLevel.LOW

    forecast = Forecast(
        business_id=business_id,
        product_id=product.id,
        horizon_days=horizon_days,
        model_used="exponential_smoothing",
        predicted_demand=predicted_demand,
        current_stock_at_run=product.current_stock,
        estimated_stockout_date=estimated_stockout_date,
        risk_level=risk_level,
        insufficient_data=False,
    )
    db.add(forecast)
    db.flush()
    return forecast
