"""
数字孪生档案：用户的基础健康信息（Pydantic 模型 + 本地 JSON 持久化）。
"""
import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

import config


class Lifestyle(BaseModel):
    """生活方式"""
    smoking: str = Field(default="", description="吸烟情况，如：不吸烟 / 每天一包")
    drinking: str = Field(default="", description="饮酒情况")
    exercise: str = Field(default="", description="运动习惯，如：每周跑步3次")
    sleep: str = Field(default="", description="作息与睡眠情况")
    diet: str = Field(default="", description="饮食习惯")


class HealthProfile(BaseModel):
    """个人健康数字孪生体 —— 基础档案"""
    name: str = Field(default="", description="姓名")
    sex: str = Field(default="", description="性别")
    age: Optional[int] = Field(default=None, description="年龄")
    height_cm: Optional[float] = Field(default=None, description="身高(cm)")
    weight_kg: Optional[float] = Field(default=None, description="体重(kg)")
    occupation: str = Field(default="", description="职业")
    blood_type: str = Field(default="", description="血型")
    chronic_conditions: List[str] = Field(default_factory=list, description="慢性病史，如高血压、2型糖尿病")
    allergies: List[str] = Field(default_factory=list, description="药物/食物过敏史")
    medications: List[str] = Field(default_factory=list, description="目前长期用药")
    family_history: List[str] = Field(default_factory=list, description="家族病史")
    lifestyle: Lifestyle = Field(default_factory=Lifestyle, description="生活方式")
    updated_at: str = Field(default="", description="最后更新时间")

    def bmi(self) -> Optional[float]:
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None

    def completeness(self) -> float:
        """档案完整度（0~1），用于 UI 展示。"""
        fields = [
            self.name, self.sex, self.age, self.height_cm, self.weight_kg,
            self.occupation, self.blood_type,
            self.chronic_conditions, self.allergies, self.medications,
            self.family_history,
            self.lifestyle.smoking, self.lifestyle.exercise, self.lifestyle.sleep,
        ]
        filled = sum(1 for f in fields if f not in ("", None, [],))
        return filled / len(fields)


class ProfileStore:
    """档案本地 JSON 存储"""

    def __init__(self, path=None):
        self.path = path or config.PROFILE_PATH

    def load(self) -> HealthProfile:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return HealthProfile.model_validate(data)
            except Exception:
                return HealthProfile()
        return HealthProfile()

    def save(self, profile: HealthProfile) -> None:
        profile.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.path.write_text(
            profile.model_dump_json(indent=2), encoding="utf-8"
        )

    def update_fields(self, **kwargs) -> HealthProfile:
        """增量更新档案字段（数字孪生自动同步入口）。"""
        profile = self.load()
        data = profile.model_dump()
        for k, v in kwargs.items():
            if v in ("", None):
                continue
            if k == "lifestyle" and isinstance(v, dict):
                data["lifestyle"].update({kk: vv for kk, vv in v.items() if vv})
                continue
            # 列表字段做去重合并
            if isinstance(v, list) and isinstance(data.get(k), list):
                merged = [x for x in data[k] if x not in v]
                data[k] = v + merged if v else data[k]
            elif v:
                data[k] = v
        profile = HealthProfile.model_validate(data)
        self.save(profile)
        return profile
