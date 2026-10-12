import uuid
from app.core.clock import utcnow

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.catalog import Product
from app.models.user import User
from app.schemas.intelligence import ForecastOut
from app.services import forecasting

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/{product_id}", response_model=ForecastOut)
def forecast_product(
    product_id: uuid.UUID,
    horizon_days: int = Query(default=14, description="7, 14 or 30"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if horizon_days not in (7, 14, 30):
        raise HTTPException(status_code=400, detail="horizon_days must be 7, 14 or 30.")
    product = db.get(Product, product_id)
    if product is None or product.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Product not found.")
    forecast = forecasting.generate_forecast(db, current_user.business_id, product, horizon_days)
    db.commit()
    db.refresh(forecast)
    return ForecastOut.model_validate(forecast)


@router.get("/{product_id}/history")
def sales_history(
    product_id: uuid.UUID,
    days: int = Query(default=60, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Daily units sold for a product (real sale_items), used to plot history next to the forecast."""
    from datetime import datetime, timedelta
    from sqlalchemy import func, select
    from app.models.sales import Sale, SaleItem, SaleStatus

    product = db.get(Product, product_id)
    if product is None or product.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Product not found.")
    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(func.date(Sale.created_at), func.sum(SaleItem.quantity))
        .join(SaleItem, SaleItem.sale_id == Sale.id)
        .where(Sale.business_id == current_user.business_id, SaleItem.product_id == product_id,
               Sale.created_at >= since, Sale.status == SaleStatus.COMPLETED)
        .group_by(func.date(Sale.created_at)).order_by(func.date(Sale.created_at))
    ).all()
    return [{"date": str(d), "units": int(u)} for d, u in rows]
