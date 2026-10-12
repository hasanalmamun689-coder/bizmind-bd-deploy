from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponse
from app.services import audit
from app.services.ai import orchestrator
from app.services.ai.tools import get_business_risks

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = orchestrator.chat(db, current_user.business_id, current_user.id,
                               payload.conversation_id, payload.message)
    audit.record(db, business_id=current_user.business_id, user_id=current_user.id,
                 action="ai.chat", entity_type="ai_conversation", entity_id=result["conversation_id"])
    db.commit()
    return ChatResponse(**result)


@router.get("/insights")
def insights(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_business_risks(db, current_user.business_id)
