import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.expense import Expense
from app.models.user import User, UserRole
from app.schemas.expense import ExpenseCreate, ExpenseOut, ExpenseUpdate
from app.services import audit

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(Expense).where(Expense.business_id == current_user.business_id)
    if date_from:
        q = q.where(Expense.expense_date >= date_from)
    if date_to:
        q = q.where(Expense.expense_date <= date_to)
    if category:
        q = q.where(Expense.category == category)
    q = q.order_by(Expense.expense_date.desc()).offset((page - 1) * page_size).limit(page_size)
    return [ExpenseOut.model_validate(e) for e in db.scalars(q).all()]


@router.get("/summary")
def expense_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(Expense.business_id == current_user.business_id)
        .group_by(Expense.category)
    ).all()
    monthly = db.execute(
        select(func.to_char(Expense.expense_date, "YYYY-MM"), func.sum(Expense.amount))
        .where(Expense.business_id == current_user.business_id)
        .group_by(func.to_char(Expense.expense_date, "YYYY-MM"))
        .order_by(func.to_char(Expense.expense_date, "YYYY-MM"))
    ).all()
    return {
        "by_category": {c.value: float(t) for c, t in rows},
        "monthly": [{"month": m, "total": float(t)} for m, t in monthly],
    }


@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(
    payload: ExpenseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    expense = Expense(business_id=current_user.business_id, created_by=current_user.id, **payload.model_dump())
    db.add(expense)
    db.flush()
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="expense.created", entity_type="expense", entity_id=expense.id,
                 metadata={"amount": payload.amount, "category": payload.category.value})
    db.commit()
    db.refresh(expense)
    return ExpenseOut.model_validate(expense)


def _owned(db, business_id, expense_id) -> Expense:
    e = db.get(Expense, expense_id)
    if e is None or e.business_id != business_id:
        raise HTTPException(status_code=404, detail="Expense not found.")
    return e


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: uuid.UUID, payload: ExpenseUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    e = _owned(db, current_user.business_id, expense_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(e, k, v)
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="expense.updated", entity_type="expense", entity_id=e.id)
    db.commit()
    db.refresh(e)
    return ExpenseOut.model_validate(e)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.OWNER)),
    db: Session = Depends(get_db),
):
    e = _owned(db, current_user.business_id, expense_id)
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="expense.deleted", entity_type="expense", entity_id=e.id,
                 metadata={"amount": float(e.amount)})
    db.delete(e)
    db.commit()
