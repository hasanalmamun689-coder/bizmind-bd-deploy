import uuid
from datetime import datetime, timedelta
from app.core.clock import utcnow

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.catalog import Product
from app.models.inventory import InventoryTransactionType
from app.models.sales import Sale, SaleItem, SaleStatus
from app.models.user import User
from app.schemas.sale import SaleCreate, SaleOut, SalesSummary
from app.services import audit
from app.services.inventory import apply_stock_change

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("", response_model=list[SaleOut])
def list_sales(
    customer_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Sale).where(Sale.business_id == current_user.business_id)
    if customer_id:
        query = query.where(Sale.customer_id == customer_id)
    if date_from:
        query = query.where(Sale.created_at >= date_from)
    if date_to:
        query = query.where(Sale.created_at <= date_to)
    if product_id:
        query = query.join(SaleItem).where(SaleItem.product_id == product_id)
    query = query.order_by(Sale.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    sales = db.scalars(query).unique().all()
    return [SaleOut(**_sale_dict(s)) for s in sales]


def _sale_dict(sale: Sale) -> dict:
    return {
        "id": sale.id,
        "customer_id": sale.customer_id,
        "total_amount": float(sale.total_amount),
        "total_cost": float(sale.total_cost),
        "gross_profit": sale.gross_profit,
        "payment_method": sale.payment_method,
        "status": sale.status,
        "created_at": sale.created_at,
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price": float(i.unit_price),
                "unit_cost": float(i.unit_cost),
                "subtotal": i.subtotal,
            }
            for i in sale.items
        ],
    }


@router.post("", response_model=SaleOut, status_code=201)
def create_sale(
    payload: SaleCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    section 11: the exact 8-step workflow — save sale, save items, reduce
    inventory, log an inventory transaction, and (via apply_stock_change)
    trigger alerts if a threshold is crossed. Everything happens in one
    DB transaction so partial sales can never occur.
    """
    sale = Sale(business_id=current_user.business_id, customer_id=payload.customer_id,
                payment_method=payload.payment_method, created_by=current_user.id)
    db.add(sale)
    db.flush()

    total_amount = 0.0
    total_cost = 0.0

    for item in payload.items:
        product = db.get(Product, item.product_id)
        if product is None or product.business_id != current_user.business_id or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} is not available.")
        if product.current_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}: {product.current_stock} available, "
                f"{item.quantity} requested.",
            )

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.selling_price,
            unit_cost=product.purchase_price,
        )
        db.add(sale_item)
        total_amount += float(product.selling_price) * item.quantity
        total_cost += float(product.purchase_price) * item.quantity

        apply_stock_change(
            db,
            business_id=current_user.business_id,
            product=product,
            delta=-item.quantity,
            txn_type=InventoryTransactionType.SALE,
            created_by=current_user.id,
            reason=f"Sale {sale.id}",
            related_sale_id=sale.id,
        )

    sale.total_amount = total_amount
    sale.total_cost = total_cost
    db.flush()

    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="sale.created",
        entity_type="sale",
        entity_id=sale.id,
        metadata={"total_amount": total_amount, "item_count": len(payload.items)},
    )
    db.commit()
    db.refresh(sale)
    return SaleOut(**_sale_dict(sale))


@router.get("/summary", response_model=SalesSummary)
def sales_summary(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = utcnow() - timedelta(days=days)
    sales = db.scalars(
        select(Sale).where(
            Sale.business_id == current_user.business_id,
            Sale.created_at >= since,
            Sale.status == SaleStatus.COMPLETED,
        )
    ).all()
    total_revenue = sum(float(s.total_amount) for s in sales)
    total_cost = sum(float(s.total_cost) for s in sales)
    count = len(sales)
    return SalesSummary(
        total_revenue=total_revenue,
        total_cost=total_cost,
        gross_profit=total_revenue - total_cost,
        total_transactions=count,
        average_order_value=round(total_revenue / count, 2) if count else 0,
    )


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sale = db.get(Sale, sale_id)
    if sale is None or sale.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Sale not found.")
    return SaleOut(**_sale_dict(sale))


@router.post("/{sale_id}/cancel", response_model=SaleOut)
def cancel_sale(sale_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    section 11: cancel a sale. Stock is returned through the same inventory
    service (so the ledger, status and alerts stay consistent) and the sale is
    kept, marked cancelled, and excluded from revenue/analytics.
    """
    sale = db.get(Sale, sale_id)
    if sale is None or sale.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Sale not found.")
    if sale.status == SaleStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="This sale is already cancelled.")

    for item in sale.items:
        product = db.get(Product, item.product_id)
        apply_stock_change(
            db,
            business_id=current_user.business_id,
            product=product,
            delta=item.quantity,
            txn_type=InventoryTransactionType.ADJUSTMENT,
            created_by=current_user.id,
            reason=f"Sale {sale.id} cancelled",
            related_sale_id=sale.id,
        )
    sale.status = SaleStatus.CANCELLED
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="sale.cancelled",
        entity_type="sale",
        entity_id=sale.id,
        metadata={"total_amount": float(sale.total_amount)},
    )
    db.commit()
    db.refresh(sale)
    return SaleOut(**_sale_dict(sale))
