import logging

from openai import OpenAI
from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import kb_service

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是「图书馆选座借阅系统」的智能助手，回答要简洁、准确。
如果下面提供了图书馆的资料，请依据资料回答，不要编造资料里没有的时间、规则、书籍。
你目前查询不到真实的区域、座位、图书和预约数据，请不要编造具体数据。
如果用户询问某个区域开放时间、某本书是否可借、某个座位是否空闲等，请引导其到对应页面查看。
如果用户问了跟当前系统无关的问题，可以直接拒绝回答。
"""



def get_client() -> OpenAI:

    """创建OPENAI的客户端请求"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的API_KEy")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

def chat(data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    # 取出用户最新的一条提问内容
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )

    knowledge = ""
    try:
        knowledge = kb_service.search(query=question)
    except Exception:
        logger.exception("知识库检索失败，将使用基础提示词继续对话")

    system_prompt = SYSTEM_PROMPT
    if knowledge:
        system_prompt += "\n\n以下是检索到的图书馆资料：\n" + knowledge

    client = get_client()

    try:
        res = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
            ],
        )
        message = res.choices[0].message
        if not message or not message.content.strip():
            raise BusinessException(message="大模型没有返回内容")
        return ChatMessage(role="assistant", content=message.content)
    except BusinessException:
        raise
    except Exception as exc:
        logger.exception("大模型调用失败: %s", exc)
        raise BusinessException(message="大模型调用失败")
