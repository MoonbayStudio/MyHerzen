from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.app.core.deps import get_optional_user
from backend.app.core.features import require_ai_agent_enabled
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from backend.app.services.assistant_service import run_assistant_chat


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
