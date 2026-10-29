"""
病历生成链 + 数字孪生档案自动同步：
  1. RECORD_PROMPT 把问诊对话转成规范门诊病历（Markdown）；
  2. with_structured_output 从病历中抽取档案字段（年龄/性别/慢病/过敏...），
     自动回写到数字孪生档案，实现"问诊 → 病历 → 孪生体同步"闭环。
"""
from typing import Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from core.llm import call_structured
from core.prompts import RECORD_PROMPT
from twin.profile import ProfileStore
from twin.records import save_record


class ProfileExtraction(BaseModel):
    """从病历中可抽取的档案字段"""
    age: Optional[int] = Field(default=None, description="年龄")
    sex: Optional[str] = Field(default=None, description="性别")
    occupation: Optional[str] = Field(default=None, description="职业")
    chief_complaint: Optional[str] = Field(default=None, description="主诉")
    chronic_conditions: Optional[List[str]] = Field(default=None, description="慢性病史")
    allergies: Optional[List[str]] = Field(default=None, description="过敏史")
    medications: Optional[List[str]] = Field(default=None, description="长期用药")
    family_history: Optional[List[str]] = Field(default=None, description="家族史")
    smoking: Optional[str] = Field(default=None, description="吸烟情况")
    drinking: Optional[str] = Field(default=None, description="饮酒情况")


def dialog_to_text(dialog: List[Dict[str, str]]) -> str:
    lines = []
    for m in dialog:
        role = "患者" if m["role"] == "user" else "医生"
        lines.append(f"{role}：{m['content']}")
    return "\n".join(lines)


class RecordWriterChain:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.chain = RECORD_PROMPT | llm | StrOutputParser()

    def generate(self, dialog: List[Dict[str, str]]) -> str:
        """由问诊对话生成病历文本。"""
        return self.chain.invoke({"dialog": dialog_to_text(dialog)})

    def extract_and_sync_profile(self, record_text: str) -> Optional[ProfileExtraction]:
        """从病历抽取档案字段并同步到数字孪生档案。"""
        extraction = call_structured(
            self.llm,
            ProfileExtraction,
            [
                ("system", "你是医疗信息抽取助手，请从病历中抽取结构化字段，缺失字段填 null。"),
                ("human", record_text[:3000]),
            ],
        )
        if extraction is None:
            return None
        store = ProfileStore()
        profile = store.load()
        kwargs = {}
        for key in ("age", "sex", "occupation", "chronic_conditions", "allergies",
                    "medications", "family_history", "smoking", "drinking"):
            val = getattr(extraction, key, None)
            if val is None or val == [] or val == "":
                continue
            # 已有同名基础信息时不覆盖（病历优先级低于用户手工填写）
            if key in ("age", "sex", "occupation") and getattr(profile, key, None):
                continue
            kwargs[key] = val
        if kwargs:
            lifestyle = {}
            if "smoking" in kwargs:
                lifestyle["smoking"] = kwargs.pop("smoking")
            if "drinking" in kwargs:
                lifestyle["drinking"] = kwargs.pop("drinking")
            if lifestyle:
                kwargs["lifestyle"] = lifestyle
            store.update_fields(**kwargs)
        return extraction

    def generate_and_save(self, dialog: List[Dict[str, str]]) -> dict:
        """完整流程：生成病历 → 抽取同步档案 → 落盘保存。"""
        record_text = self.generate(dialog)
        self.extract_and_sync_profile(record_text)
        rec = save_record(record_text)
        return {"record": record_text, "meta": rec}
