"""
数字孪生上下文构建器：把档案 + 指标趋势 + 病历摘要整合成一段
可直接注入提示词的文本（"数字孪生体"的数据视图）。
"""
from typing import Optional

from twin.profile import ProfileStore


def build_twin_context(include_records: bool = True, max_records: int = 5,
                       max_record_chars: int = 300) -> str:
    """生成注入 LLM 提示词的孪生体上下文。"""
    from twin.metrics import MetricStore
    from twin.records import list_records

    profile = ProfileStore().load()
    parts: list = []

    # ---- 基础档案 ----
    basic = []
    if profile.name:
        basic.append(f"姓名：{profile.name}")
    if profile.sex:
        basic.append(f"性别：{profile.sex}")
    if profile.age:
        basic.append(f"年龄：{profile.age}岁")
    if profile.occupation:
        basic.append(f"职业：{profile.occupation}")
    if profile.height_cm or profile.weight_kg:
        h = f"{profile.height_cm:.0f}cm" if profile.height_cm else "未记录"
        w = f"{profile.weight_kg:.1f}kg" if profile.weight_kg else "未记录"
        basic.append(f"身高/体重：{h} / {w}")
        bmi = profile.bmi()
        if bmi:
            basic.append(f"BMI：{bmi}")
    if profile.chronic_conditions:
        basic.append(f"慢性病史：{'、'.join(profile.chronic_conditions)}")
    if profile.allergies:
        basic.append(f"过敏史：{'、'.join(profile.allergies)}")
    if profile.medications:
        basic.append(f"长期用药：{'、'.join(profile.medications)}")
    if profile.family_history:
        basic.append(f"家族史：{'、'.join(profile.family_history)}")
    ls = profile.lifestyle
    lifestyle = "；".join(
        f"{k}：{v}" for k, v in [
            ("吸烟", ls.smoking), ("饮酒", ls.drinking), ("运动", ls.exercise),
            ("睡眠", ls.sleep), ("饮食", ls.diet),
        ] if v
    )
    if lifestyle:
        basic.append(f"生活方式：{lifestyle}")

    if basic:
        parts.append("【基础档案】\n" + "\n".join(basic))
    else:
        parts.append("【基础档案】（用户尚未填写，可在「数字孪生档案」页完善）")

    # ---- 指标趋势 ----
    parts.append("【近期指标趋势】\n" + MetricStore().summary())

    # ---- 病历摘要 ----
    if include_records:
        records = list_records()[:max_records]
        if records:
            lines = [f"- {r['title']}（{r['time']}）：{r['content'][:max_record_chars]}..." for r in records]
            parts.append("【历史病历摘要】\n" + "\n".join(lines))
        else:
            parts.append("【历史病历摘要】（暂无病历）")

    return "\n\n".join(parts)
