"""
数字孪生体综合评估链：档案 + 指标趋势 + 历史病历 → 孪生体画像、风险分层、
个性化干预建议与监测计划。
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from core.prompts import TWIN_PROMPT
from twin.context import build_twin_context


class TwinAnalystChain:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.chain = TWIN_PROMPT | llm | StrOutputParser()

    def assess(self, max_records: int = 8) -> str:
        twin_context = build_twin_context(include_records=True, max_records=max_records)
        return self.chain.invoke({"twin_context": twin_context})
