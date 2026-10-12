from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.ai import AuditLogOut
from app.schemas.auth import UserOut
from pydantic import BaseModel, EmailStr, Field
from app.services import audit

router = APIRouter(prefix="/api", tags=["administration"])


class EmployeeCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    job_title: str | None = None
    role: UserRole = UserRole.MANAGER


@router.get("/employees", response_model=list[UserOut])
def employees(current_user: User = Depends(require_role(UserRole.OWNER)), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.business_id == current_user.business_id)).all()
    return [UserOut.model_validate(u) for u in rows]


@router.post("/employees", response_model=UserOut, status_code=201)
def create_employee(payload: EmployeeCreate, current_user: User = Depends(require_role(UserRole.OWNER)),
                    db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    user = User(business_id=current_user.business_id, email=payload.email,
                password_hash=hash_password(payload.password), full_name=payload.full_name,
                job_title=payload.job_title, role=payload.role)
    db.add(user)
    db.flush()
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="employee.created", entity_type="user", entity_id=user.id,
                 metadata={"role": payload.role.value})
    db.commit()
    return UserOut.model_validate(user)


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(page: int = Query(default=1, ge=1), page_size: int = Query(default=50, le=200),
               current_user: User = Depends(require_role(UserRole.OWNER)), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(AuditLog).where(AuditLog.business_id == current_user.business_id)
        .order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [AuditLogOut.model_validate(r) for r in rows]


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    industry: str | None = None
    address: str | None = None


def _settings_payload(db: Session, user: User) -> dict:
    from app.core.config import settings as cfg
    from app.models.business import Business

    biz = db.get(Business, user.business_id)
    return {
        "business": {"name": biz.name, "industry": biz.industry, "address": biz.address, "currency": biz.currency},
        # Never returns the API key — only whether a live AI provider is active.
        "system": {
            "environment": cfg.ENVIRONMENT,
            "ai_provider": cfg.AI_PROVIDER if (cfg.AI_PROVIDER != "none" and cfg.AI_API_KEY) else "none",
            "ai_mode": "live_model" if (cfg.AI_PROVIDER == "anthropic" and cfg.AI_API_KEY) else "deterministic_fallback",
        },
    }


@router.get("/settings")
def get_settings_view(current_user: User = Depends(require_role(UserRole.OWNER)), db: Session = Depends(get_db)):
    return _settings_payload(db, current_user)


@router.put("/settings/business")
def update_business(payload: BusinessUpdate, current_user: User = Depends(require_role(UserRole.OWNER)),
                    db: Session = Depends(get_db)):
    from app.models.business import Business

    biz = db.get(Business, current_user.business_id)
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(biz, k, v)
    audit.record(db, business_id=biz.id, user_id=current_user.id, action="settings.business_updated",
                 entity_type="business", entity_id=biz.id, metadata={"fields": sorted(changes)})
    db.commit()
    return _settings_payload(db, current_user)
