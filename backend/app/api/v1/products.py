import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.catalog import Category, Product
from app.models.user import User, UserRole
from app.schemas.product import CategoryCreate, CategoryOut, ProductCreate, ProductOut, ProductUpdate
from app.services import audit

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Product).where(Product.business_id == current_user.business_id)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    if category_id:
        query = query.where(Product.category_id == category_id)
    if status_filter:
        query = query.where(Product.status == status_filter)
    query = query.order_by(Product.name).offset((page - 1) * page_size).limit(page_size)
    products = db.scalars(query).all()
    return [ProductOut.model_validate(p) for p in products]


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duplicate = db.scalar(
        select(Product.id).where(Product.business_id == current_user.business_id, Product.sku == payload.sku)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail=f"A product with SKU {payload.sku} already exists.")
    product = Product(business_id=current_user.business_id, **payload.model_dump())
    product.recompute_status()
    db.add(product)
    db.flush()
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="product.created",
        entity_type="product",
        entity_id=product.id,
        metadata={"name": product.name, "sku": product.sku},
    )
    db.commit()
    db.refresh(product)
    return ProductOut.model_validate(product)


def _get_owned_product(db: Session, business_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.business_id != business_id:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    product = _get_owned_product(db, current_user.business_id, product_id)
    return ProductOut.model_validate(product)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = _get_owned_product(db, current_user.business_id, product_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    product.recompute_status()
    db.flush()
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="product.updated",
        entity_type="product",
        entity_id=product.id,
    )
    db.commit()
    db.refresh(product)
    return ProductOut.model_validate(product)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    """Archive rather than hard-delete, so sales history stays intact (section 12)."""
    product = _get_owned_product(db, current_user.business_id, product_id)
    product.is_active = False
    audit.record(
        db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="product.archived",
        entity_type="product",
        entity_id=product.id,
    )
    db.commit()


@router.get("/meta/categories", response_model=list[CategoryOut])
def list_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Category).where(Category.business_id == current_user.business_id).order_by(Category.name)
    ).all()


@router.post("/meta/categories", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    category = Category(business_id=current_user.business_id, name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
