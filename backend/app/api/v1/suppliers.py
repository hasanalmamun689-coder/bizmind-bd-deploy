import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.catalog import Product
from app.models.supplier import Supplier, SupplierPriceHistory, SupplierProduct
from app.models.user import User
from app.schemas.supplier import SupplierComparisonRow, SupplierCreate, SupplierOut, SupplierPriceSet
from app.services import audit

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    suppliers = db.scalars(
        select(Supplier).where(Supplier.business_id == current_user.business_id).order_by(Supplier.name)
    ).all()
    return [SupplierOut.model_validate(s) for s in suppliers]


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(
    payload: SupplierCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    supplier = Supplier(business_id=current_user.business_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)


@router.get("/compare", response_model=list[SupplierComparisonRow])
def compare_suppliers(
    product_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    section 15: show the underlying evidence (price, delivery, reliability,
    quality, fulfillment, payment terms) rather than collapsing everything
    into one opaque score.
    """
    rows = db.execute(
        select(Supplier, SupplierProduct)
        .join(SupplierProduct, SupplierProduct.supplier_id == Supplier.id)
        .where(Supplier.business_id == current_user.business_id, SupplierProduct.product_id == product_id)
    ).all()

    results = []
    for supplier, sp in rows:
        note = (
            f"Delivery in {supplier.delivery_time_days}d, "
            f"{supplier.reliability_score}/100 reliability, "
            f"{supplier.quality_score}/100 quality, "
            f"{supplier.fulfillment_rate}% fulfillment"
        )
        results.append(
            SupplierComparisonRow(
                supplier=SupplierOut.model_validate(supplier),
                price=float(sp.price),
                minimum_order_quantity=sp.minimum_order_quantity,
                composite_note=note,
            )
        )
    return sorted(results, key=lambda r: r.price or 0)


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return SupplierOut.model_validate(supplier)


@router.put("/{supplier_id}/prices", response_model=SupplierComparisonRow)
def set_supplier_price(
    supplier_id: uuid.UUID,
    payload: SupplierPriceSet,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update the price a supplier quotes for a product; every quote is kept in history."""
    supplier = db.get(Supplier, supplier_id)
    product = db.get(Product, payload.product_id)
    if supplier is None or supplier.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    if product is None or product.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Product not found.")

    sp = db.scalar(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id, SupplierProduct.product_id == payload.product_id
        )
    )
    previous = float(sp.price) if sp else None
    if sp is None:
        sp = SupplierProduct(supplier_id=supplier_id, product_id=payload.product_id,
                             price=payload.price, minimum_order_quantity=payload.minimum_order_quantity)
        db.add(sp)
    else:
        sp.price = payload.price
        sp.minimum_order_quantity = payload.minimum_order_quantity
    if previous != payload.price:
        db.add(SupplierPriceHistory(supplier_id=supplier_id, product_id=payload.product_id, price=payload.price))
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="supplier.price_set", entity_type="supplier", entity_id=supplier_id,
                 metadata={"product_id": str(payload.product_id), "previous": previous, "price": payload.price})
    db.commit()
    return SupplierComparisonRow(
        supplier=SupplierOut.model_validate(supplier), price=float(sp.price),
        minimum_order_quantity=sp.minimum_order_quantity, composite_note="Price saved.")
