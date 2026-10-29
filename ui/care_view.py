"""
视图：智能就医匹配 —— 症状 → 科室推荐（知识库 grounding + LLM 结构化输出）
"""
import streamlit as st

from agents.care_matcher import URGENCY_LABEL, CareMatcherChain


def _render_result(result):
    rec: "CareRecommendation" = result["result"]

    # 紧急程度
    urgency = URGENCY_LABEL.get(rec.urgency, rec.urgency)
    if rec.urgency == "urgent":
        st.error(f"**建议：{urgency}** —— 请立即前往急诊或拨打 120")
    elif rec.urgency == "soon":
        st.warning(f"**建议：{urgency}** —— 请在近 1-3 天内挂号就诊")
    else:
        st.success(f"**建议：{urgency}**")

    # 推荐科室
    st.markdown("#### 🏥 推荐就诊科室")
    for i, dep in enumerate(rec.recommended_departments, 1):
        with st.container(border=True):
            st.markdown(f"**{i}. {dep.department}**")
            st.markdown(f"推荐理由：{dep.reason}")

    left, right = st.columns(2)
    with left:
        if rec.red_flags:
            st.markdown("#### 🚨 需立即就医的警示信号")
            for f in rec.red_flags:
                st.markdown(f"- ⚠️ {f}")
        if rec.preparation_checklist:
            st.markdown("#### 🎒 就诊前准备")
            for c in rec.preparation_checklist:
                st.markdown(f"- ☑️ {c}")
    with right:
        if rec.questions_to_ask:
            st.markdown("#### ❓ 建议向医生咨询的问题")
            for q in rec.questions_to_ask:
                st.markdown(f"- 💬 {q}")
        if rec.general_advice:
            st.markdown("#### 💡 就诊前建议")
            st.info(rec.general_advice)


def render(get_llm, get_kb):
    st.subheader("🏥 智能就医匹配")
    st.caption("结合本地科室知识库与你的数字孪生档案，给出结构化的科室推荐、就诊准备与问诊问题清单")

    symptom = st.text_area(
        "症状 / 主诉描述",
        height=120,
        placeholder="例如：最近一周头晕、心悸，测量血压 150/95，有高血压家族史，应该挂什么科？",
    )

    if st.button("🔍 开始匹配", type="primary", use_container_width=True) and symptom.strip():
        matcher = CareMatcherChain(get_llm(temperature=0.3))
        with st.spinner("知识库检索 + AI 分析中..."):
            try:
                result = matcher.match(symptom.strip())
            except Exception as e:
                st.error(f"匹配失败：{e}\n\n如持续出现，请稍后再试或联系管理员。")
                st.stop()
        st.session_state.care_result = result

    result = st.session_state.get("care_result")
    if result:
        # 知识库命中（确定性检索部分）
        hits = result["kb_hits"]
        if hits:
            hit_text = "、".join(f"{h['department']}({h['score']})" for h in hits[:4])
            st.caption(f"🔎 本地知识库命中：{hit_text}")

        if result["result"] is not None:
            _render_result(result)
        else:
            st.warning("结构化解析失败，可能是模型能力不足，请换用更强的模型后重试。")

    st.divider()
    st.caption("⚠️ 免责声明：科室推荐仅作导诊参考，不构成医疗诊断；急症请直接拨打 120 或前往急诊。")
