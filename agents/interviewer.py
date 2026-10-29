"""
AI 智能问诊链：模拟真实医生循序渐进地问诊（单轮只问一个问题）。
"""
from typing import Dict, Iterator, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from agents.consultant import _to_lc_messages
from core.prompts import INTERVIEW_PROMPT
from twin.context import build_twin_context

KICKOFF = "医生您好，我最近身体不太舒服，想请您帮我看诊。（请开始问诊）"


class InterviewChain:
    """问诊链：dialog 为 [{"role":"user"/"assistant","content":...}]"""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.chain = INTERVIEW_PROMPT | llm | StrOutputParser()

    def stream_reply(self, dialog: List[Dict[str, str]], user_input: str) -> Iterator[str]:
        """基于已有问诊对话 + 患者最新输入，流式生成医生的下一个问题/总结。"""
        inputs = {
            "history": _to_lc_messages(dialog[-20:]),
            "question": user_input,
        }
        for chunk in self.chain.stream(inputs):
            yield chunk
