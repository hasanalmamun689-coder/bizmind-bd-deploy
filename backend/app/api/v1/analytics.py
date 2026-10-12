from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.intelligence import BusinessHealthScore
from app.services import analytics
from app.services.health_score import compute_business_health_score

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = current_user.business_id
    return {
        "kpis": analytics.dashboard_kpis(db, bid),
        "sales_trend": analytics.sales_trend(db, bid, days=30),
        "top_products": analytics.top_products(db, bid, limit=5),
        "unresolved_alerts": analytics.unresolved_alert_count(db, bid),
    }


@router.get("/sales")
def sales(days: int = Query(default=30, ge=1, le=365),
          current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = current_user.business_id
    return {"trend": analytics.sales_trend(db, bid, days=days), "top_products": analytics.top_products(db, bid, 10)}


@router.get("/profit")
def profit(days: int = Query(default=30, ge=1, le=365),
           current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.profit_breakdown(db, current_user.business_id, days=days)


@router.get("/inventory")
def inventory(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.inventory_analytics(db, current_user.business_id)


@router.get("/suppliers")
def suppliers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.supplier_analytics(db, current_user.business_id)


@router.get("/health-score", response_model=BusinessHealthScore)
def health_score(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return compute_business_health_score(db, current_user.business_id)


@router.get("/monthly")
def monthly(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.monthly_financials(db, current_user.business_id)


@router.get("/categories")
def categories(days: int = Query(default=30, ge=1, le=365),
               current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.category_performance(db, current_user.business_id, days=days)


@router.get("/inventory-movement")
def inventory_movement(days: int = Query(default=30, ge=1, le=365),
                       current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.inventory_movement(db, current_user.business_id, days=days)
