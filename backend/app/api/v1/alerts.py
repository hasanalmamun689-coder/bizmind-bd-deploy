import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.intelligence import Alert, AlertStatus
from app.models.user import User
from app.schemas.intelligence import AlertOut, RiskOut
from app.services.risk import detect_business_risks

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    severity: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(Alert).where(Alert.business_id == current_user.business_id)
    if severity:
        q = q.where(Alert.severity == severity)
    if status:
        q = q.where(Alert.status == status)
    return [AlertOut.model_validate(a) for a in db.scalars(q.order_by(Alert.created_at.desc())).all()]


@router.get("/risks", response_model=list[RiskOut])
def risks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_business_risks(db, current_user.business_id)


@router.put("/{alert_id}/status", response_model=AlertOut)
def update_alert_status(
    alert_id: uuid.UUID, new_status: AlertStatus,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    alert = db.get(Alert, alert_id)
    if alert is None or alert.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.status = new_status
    db.commit()
    db.refresh(alert)
    return AlertOut.model_validate(alert)
