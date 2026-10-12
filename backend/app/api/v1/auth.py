from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.business import Business
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    business = Business(name=payload.business_name)
    db.add(business)
    db.flush()

    # The first user of a new business is always the owner (section 8).
    user = User(
        business_id=business.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        job_title=payload.job_title or "Owner",
        role=UserRole.OWNER,
    )
    db.add(user)
    db.flush()

    audit.record(
        db,
        business_id=business.id,
        user_id=user.id,
        action="user.registered",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    audit.record(
        db,
        business_id=user.business_id,
        user_id=user.id,
        action="user.logged_in",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
