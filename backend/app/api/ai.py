from fastapi import APIRouter, Depends
from app.common.response import Response
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.services import ai_service


router = APIRouter(prefix="/ai", tags=["AI相关的API"])


@router.post("/chat")
def chat(data: ChatRequest, current_user: User = Depends(get_current_user)):
    message = ai_service.chat(data)
    return Response.success(data=message)
