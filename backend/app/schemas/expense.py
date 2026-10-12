import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.expense import ExpenseCategory


class ExpenseCreate(BaseModel):
    category: ExpenseCategory
    amount: float = Field(gt=0)
    description: str | None = None
    expense_date: date


class ExpenseUpdate(BaseModel):
    category: ExpenseCategory | None = None
    amount: float | None = Field(default=None, gt=0)
    description: str | None = None
    expense_date: date | None = None


class ExpenseOut(BaseModel):
    id: uuid.UUID
    category: ExpenseCategory
    amount: float
    description: str | None
    expense_date: date
    created_at: datetime

    model_config = {"from_attributes": True}
