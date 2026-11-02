"""
智能就医匹配链：症状 → 就诊科室推荐（结构化输出）。

设计（对应申报书"智能就医匹配"模块）：
  1. 本地科室知识库（knowledge/departments.json）先做关键词命中，作为确定性 grounding；
  2. 命中条目 + 用户数字孪生档案一起注入提示词；
  3. LangChain with_structured_output 输出 Pydantic 结构化推荐结果
     （供应商不支持工具调用时自动降级为 JSON 提示词解析）。
"""
import json
from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

import config
from core.llm import call_structured
from core.prompts import CARE_MATCH_PROMPT
from twin.profile import ProfileStore


class DepartmentRecommendation(BaseModel):
    """单个科室推荐"""
    department: str = Field(description="科室名称")
    reason: str = Field(description="推荐理由，结合患者症状与个人史")


class CareRecommendation(BaseModel):
    """结构化就医推荐结果"""
    urgency: str = Field(description="紧急程度：routine(常规就诊) / soon(尽快就诊) / urgent(紧急就医)")
    recommended_departments: List[DepartmentRecommendation] = Field(description="按优先级排序的推荐科室，最多3个")
    red_flags: List[str] = Field(default_factory=list, description="出现哪些情况需要立即急诊")
    preparation_checklist: List[str] = Field(default_factory=list, description="就诊前准备材料与事项")
    questions_to_ask: List[str] = Field(default_factory=list, description="建议向医生咨询的问题")
    general_advice: str = Field(default="", description="就诊前的一般性建议")


URGENCY_LABEL = {"routine": "常规就诊", "soon": "尽快就诊", "urgent": "⚠️ 紧急就医"}

# 常见口语症状 -> 知识库标准词（命中前置换，让"发烧/拉肚子"这类口语也能命中科室）
SYNONYMS = {
    "发烧": "发热", "拉肚子": "腹泻", "肚子疼": "腹痛", "肚子痛": "腹痛", "腹泄": "腹泻",
    "胸口疼": "胸痛", "胸口痛": "胸痛", "心口疼": "胸痛", "心口痛": "胸痛",
    "牙疼": "牙痛", "血压高": "高血压", "血糖高": "血糖", "心慌": "心悸",
    "喘不上气": "呼吸困难", "浑身没劲": "乏力", "起夜多": "尿频",
    "睡不着": "失眠", "掉头发": "脱发", "起疹子": "皮疹", "恶心想吐": "恶心呕吐",
}


def _expand_colloquial(symptom: str) -> str:
    extras = [std for slang, std in SYNONYMS.items() if slang in symptom]
    return symptom + (" " + " ".join(extras) if extras else "")


def load_departments() -> dict:
    path = config.KNOWLEDGE_DIR / "departments.json"
    return json.loads(path.read_text(encoding="utf-8"))


def keyword_match(symptom: str, top_n: int = 6) -> List[dict]:
    """知识库关键词命中（确定性检索，作为 LLM 的 grounding）。"""
    departments = load_departments()
    hits = []
    for name, info in departments.items():
        score = sum(1 for kw in info["keywords"] if kw in symptom)
        if score > 0:
            hits.append({"department": name, "score": score, "note": info["note"],
                         "matched": [kw for kw in info["keywords"] if kw in symptom]})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_n]


def _profile_brief() -> str:
    p = ProfileStore().load()
    parts = []
    if p.sex or p.age:
        seg = p.sex or ""
        if p.age:
            seg += ("，" if seg else "") + f"{p.age}岁"
        parts.append(seg)
    if p.chronic_conditions:
        parts.append(f"慢病史：{'、'.join(p.chronic_conditions)}")
    if p.medications:
        parts.append(f"用药：{'、'.join(p.medications)}")
    if p.allergies:
        parts.append(f"过敏：{'、'.join(p.allergies)}")
    return "；".join(parts) if parts else "（未填写个人档案）"


class CareMatcherChain:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def match(self, symptom: str) -> dict:
        """返回 {"kb_hits": [...], "result": CareRecommendation}
        结构化调用失败时直接抛 RuntimeError（携带真实原因，如网络/密钥/服务端错误）。"""
        hits = keyword_match(_expand_colloquial(symptom))
        kb_text = "\n".join(
            f"- {h['department']}（{h['note']}）命中关键词：{'、'.join(h['matched'])}" for h in hits
        ) or "（知识库未直接命中，请依据医学知识判断）"

        messages = [
            ("system", "你是导诊顾问。输出必须为结构化推荐结果，科室名称使用中国医院的标准科室名。"),
            ("human", CARE_MATCH_PROMPT.format(
                profile_brief=_profile_brief(),
                symptom=symptom,
                kb_hits=kb_text,
            )),
        ]
        result = call_structured(self.llm, CareRecommendation, messages)
        if result is None:
            raise RuntimeError("结构化输出返回为空，请稍后重试或更换模型")
        # 提示词里的"最多3个"对模型只是软约束，这里硬性截断
        result.recommended_departments = result.recommended_departments[:3]
        return {"kb_hits": hits, "result": result}
