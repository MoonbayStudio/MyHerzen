from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.deps import get_optional_user
from app.core.features import require_ai_agent_enabled
from app.db.models import User
from app.db.session import get_db
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.assistant_service import run_assistant_chat


router = APIRouter()


@router.post("/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    request: Request,
    data: AssistantChatRequest,
    _: None = Depends(require_ai_agent_enabled),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    return await run_assistant_chat(
        request=request,
        data=data,
        db=db,
        current_user=current_user,
    )
