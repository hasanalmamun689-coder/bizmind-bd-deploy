import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.intelligence import AlertSeverity, AlertStatus, RecommendationStatus, RiskLevel


class ForecastOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    horizon_days: int
    model_used: str
    predicted_demand: float
    current_stock_at_run: int
    estimated_stockout_date: date | None
    risk_level: RiskLevel
    insufficient_data: bool
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class AlertOut(BaseModel):
    id: uuid.UUID
    type: str
    severity: AlertSeverity
    title: str
    description: str
    related_entity_type: str | None
    related_entity_id: uuid.UUID | None
    suggested_action: str | None
    status: AlertStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskOut(BaseModel):
    """A live-computed risk signal (section 21) — not persisted like Alert."""

    risk: str
    severity: AlertSeverity
    evidence: dict
    explanation: str
    recommended_investigation: str


class RecommendationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    evidence: dict
    reasoning: str
    suggested_action: str
    status: RecommendationStatus
    related_purchase_order_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BusinessHealthComponent(BaseModel):
    name: str
    score: float
    detail: str


class BusinessHealthScore(BaseModel):
    overall_score: float
    components: list[BusinessHealthComponent]
    disclaimer: str = (
        "This is a transparent, rule-based indicator built from the components "
        "listed below — not a certified or universal financial score."
    )
