"""
智能健康咨询链：RAG（个人健康资料检索）+ 多轮对话记忆 + 流式输出。
LCEL: CONSULTANT_PROMPT | llm，通过 .stream() 逐块产出。
"""
from typing import Dict, Iterator, List, Optional, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from core.prompts import CONSULTANT_PROMPT
from core.retriever import KnowledgeBase
from twin.context import build_twin_context


def _to_lc_messages(history: List[Dict[str, str]]) -> List[BaseMessage]:
    """把 [{"role","content"}] 转成 LangChain 消息对象。"""
    msgs: List[BaseMessage] = []
    for m in history:
        if m["role"] == "user":
            msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            msgs.append(AIMessage(content=m["content"]))
    return msgs


class ConsultantChain:
    """健康咨询链（对话历史由调用方维护，注入 MessagesPlaceholder）。"""

    def __init__(self, llm: BaseChatModel, kb: Optional[KnowledgeBase] = None):
        self.llm = llm
        self.kb = kb
        self.chain = CONSULTANT_PROMPT | llm | StrOutputParser()

    def retrieve_context(self, question: str) -> str:
        if self.kb is None:
            return "（未启用知识库检索）"
        docs = self.kb.search(question)
        if not docs:
            return "（未检索到相关资料）"
        blocks = []
        for d in docs:
            src = {"medical_record": "病历", "health_report": "健康报告", "twin_profile": "孪生档案"}.get(
                d.metadata.get("source", ""), "资料"
            )
            t = d.metadata.get("time", "")
            blocks.append(f"[{src}{' ' + t if t else ''}]\n{d.page_content[:1500]}")
        return "\n\n".join(blocks)

    def stream_answer(self, question: str, history: List[Dict[str, str]],
                      twin_context: Optional[str] = None) -> Iterator[str]:
        """流式生成回答。history 不含本轮 question。"""
        context = self.retrieve_context(question)
        inputs = {
            "history": _to_lc_messages(history[-12:]),  # 近 12 轮作为记忆窗口
            "twin_context": twin_context or build_twin_context(include_records=False),
            "context": context,
            "question": question,
        }
        for chunk in self.chain.stream(inputs):
            yield chunk
