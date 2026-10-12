import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerOut
from app.services import analytics

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customers = db.scalars(
        select(Customer).where(Customer.business_id == current_user.business_id).order_by(Customer.name)
    ).all()
    result = []
    for c in customers:
        summary = analytics.customer_summary(db, current_user.business_id, c)
        result.append(
            CustomerOut(
                id=c.id,
                name=c.name,
                contact=c.contact,
                created_at=c.created_at,
                total_spent=summary["total_spent"],
                total_orders=summary["total_orders"],
                last_purchase_at=summary["last_purchase_at"],
                segment=summary["segment"],
            )
        )
    return result


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    customer = Customer(business_id=current_user.business_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return CustomerOut(
        id=customer.id, name=customer.name, contact=customer.contact, created_at=customer.created_at
    )


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    customer = db.get(Customer, customer_id)
    if customer is None or customer.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Customer not found.")
    summary = analytics.customer_summary(db, current_user.business_id, customer)
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        contact=customer.contact,
        created_at=customer.created_at,
        **summary,
    )
