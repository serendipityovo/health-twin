"""
LLM 工厂：统一创建在线（OpenAI 兼容）或离线（Ollama）大模型。

上层业务（agents/）只依赖 LangChain 的 BaseChatModel 抽象，
切换模型供应商时无需改动任何业务代码。
"""
import json
import re
from typing import List, Optional, Sequence, Type, TypeVar, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

import config

T = TypeVar("T", bound=object)


def get_chat_model(temperature: Optional[float] = None, streaming: bool = True) -> BaseChatModel:
    """创建 DeepSeek 聊天模型（写死，用户无需配置）。"""
    temperature = config.TEMPERATURE if temperature is None else temperature

    if config.LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
            temperature=temperature,
            num_predict=config.MAX_TOKENS,
        )

    if not config.DEEPSEEK_API_KEY:
        if config.DEV_MODE:
            raise ValueError(
                "开发者模式：尚未配置 DEEPSEEK_API_KEY，"
                "请在项目目录 .env 中填写，或在本页「🛠 开发者选项」中配置。"
            )
        raise ValueError("AI 服务暂未开通，请联系管理员开通后使用。")

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=config.ONLINE_BASE_URL,
        api_key=config.DEEPSEEK_API_KEY,
        model=config.ONLINE_MODEL,
        temperature=temperature,
        max_tokens=config.MAX_TOKENS,
        timeout=config.REQUEST_TIMEOUT,
        streaming=streaming,
    )


def _messages_to_text(messages: Sequence[Union[str, BaseMessage]]) -> str:
    """把消息列表压成纯文本（用于结构化输出的降级提示）。"""
    from langchain_core.messages import messages_to_dict

    parts = []
    for m in messages:
        if isinstance(m, BaseMessage):
            role = {"human": "用户", "ai": "助手", "system": "系统"}.get(m.type, m.type)
            content = m.content if isinstance(m.content, str) else str(m.content)
            parts.append(f"{role}: {content}")
        else:
            parts.append(str(m))
    return "\n".join(parts)


def extract_json(text: str) -> Optional[dict]:
    """从模型输出中宽松地抽取第一个 JSON 对象（降级解析用）。"""
    text = text.strip()
    # 剥掉 ```json ... ``` 代码块
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.S)
        if brace:
            text = brace.group(0)
    try:
        return json.loads(text)
    except Exception:
        return None


def call_structured(
    llm: BaseChatModel,
    schema: Type[T],
    messages: List[Union[str, BaseMessage]],
) -> Optional[T]:
    """
    结构化输出统一入口：
      1. 优先使用 LangChain 的 with_structured_output（工具调用 / JSON 模式）；
      2. 供应商不支持时自动降级为「提示词要求 JSON + 宽松解析」。
    """
    try:
        chain = llm.with_structured_output(schema)
        result = chain.invoke(messages)
        if result is not None:
            return result
    except Exception:
        pass

    # ---- 降级路径：直接让模型输出 JSON ----
    from langchain_core.output_parsers import StrOutputParser

    schema_json = json.dumps(getattr(schema, "model_json_schema", lambda: {})(), ensure_ascii=False)
    instruction = (
        "\n\n请严格按照以下 JSON Schema 输出一个 JSON 对象，"
        "不要输出任何 JSON 之外的文字：\n" + schema_json
    )
    flat = [_messages_to_text(messages) + instruction]
    try:
        text = (llm | StrOutputParser()).invoke(flat)
        data = extract_json(text)
        if data:
            return schema.model_validate(data)  # type: ignore[attr-defined]
    except Exception:
        return None
    return None
