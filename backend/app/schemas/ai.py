import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    evidence: dict
    reasoning: str
    suggested_action: str | None = None
    used_live_model: bool


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    log_metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
