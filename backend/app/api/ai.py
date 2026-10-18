from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.common.response import Response
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.services import agent_service


router = APIRouter(prefix="/ai", tags=["AI相关的API"])


@router.post("/chat")
def chat(data: ChatRequest, current_user: User = Depends(get_current_user)):
    # 把当前登录用户交给 Agent：user_id 会放进 RunnableConfig，供“我的预约/我的预借”工具读取
    message = agent_service.chat(current_user, data)
    return Response.success(data=message)


@router.post("/chat/stream", summary="AI 对话（SSE 流式输出）")
def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """和 /chat 行为一致，但以 text/event-stream 逐步返回 token。"""
    return StreamingResponse(
        agent_service.chat_stream(current_user, data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
