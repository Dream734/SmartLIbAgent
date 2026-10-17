import logging

from openai import OpenAI
from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatMessage, ChatRequest

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是「图书馆选座借阅系统」的智能助手，回答要简洁、准确。
你可以介绍本系统的功能与使用流程：
1.选座：进入「座位预约」，选择区域、日期、开始/结束时间（只支持整点和半点，单次最长4小时），再点击座位预约
2.取消/离座：在「我的预约」中操作
3.图书：进入「图书预借」按书名/作者/ISBN 或分类查询，点击详情查看，点击预借即可预借
4.预借保留 2 天，超时自动取消；取消预借在「我的预约」的图书页签操作
你目前查询不到真实的区域、座位、图书和预约数据，请不要编造具体数据。
如果用户询问某个区域开放时间、某本书是否可借、某个座位是否空闲等，请引导其到对应页面查看。
5.如果用户问了跟当前系统无关的问题，可以直接拒绝回答。
"""

def get_client() ->OpenAI:

    """创建OPENAI的客户端请求"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的API_KEy")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

def chat(data: ChatRequest):
    if not data.messages:
        raise BusinessException(message="对话内容为空")
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message)
    if not history:
        raise BusinessException(message="请输入您要对话的内容")
    client = get_client()

    try:
        res = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                *history,
            ],
        )
        message = res.choices[0].message
        if not message or not message.content.strip():
            raise BusinessException(message="大模型没有返回内容")
        return ChatMessage(role="assistant", content=message.content)
    except Exception as exc:
        logger.exception("大模型调用失败: %s", exc)
        raise BusinessException(message="大模型调用失败")
