"""
视图：数字孪生档案 —— 档案编辑 / 指标记录与趋势 / 病历列表 / AI 孪生体评估
"""
from datetime import date

import pandas as pd
import streamlit as st

from twin.metrics import METRIC_TYPES, MetricStore
from twin.profile import Lifestyle, ProfileStore
from twin.records import delete_record, list_records


def _render_profile_form(store: ProfileStore):
    p = store.load()
    with st.form("profile_form"):
        st.markdown("##### 👤 基础档案")
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("姓名", value=p.name)
        sex = c2.selectbox("性别", ["", "男", "女"], index=["", "男", "女"].index(p.sex) if p.sex in ("", "男", "女") else 0)
        age = c3.number_input("年龄", 0, 120, value=int(p.age or 0))
        occupation = c4.text_input("职业", value=p.occupation)

        c5, c6, c7 = st.columns(3)
        height = c5.number_input("身高(cm)", 0.0, 250.0, value=float(p.height_cm or 0), step=0.5)
        weight = c6.number_input("体重(kg)", 0.0, 300.0, value=float(p.weight_kg or 0), step=0.5)
        blood_type = c7.text_input("血型", value=p.blood_type)

        st.markdown("##### 🏥 健康史")
        c8, c9 = st.columns(2)
        chronic = c8.text_input("慢性病史（逗号分隔）", value="、".join(p.chronic_conditions))
        allergies = c9.text_input("过敏史（逗号分隔）", value="、".join(p.allergies))
        c10, c11 = st.columns(2)
        medications = c10.text_input("长期用药（逗号分隔）", value="、".join(p.medications))
        family = c11.text_input("家族史（逗号分隔）", value="、".join(p.family_history))

        st.markdown("##### 🏃 生活方式")
        c12, c13, c14, c15, c16 = st.columns(5)
        smoking = c12.text_input("吸烟", value=p.lifestyle.smoking)
        drinking = c13.text_input("饮酒", value=p.lifestyle.drinking)
        exercise = c14.text_input("运动", value=p.lifestyle.exercise)
        sleep = c15.text_input("睡眠", value=p.lifestyle.sleep)
        diet = c16.text_input("饮食", value=p.lifestyle.diet)

        if st.form_submit_button("💾 保存档案", type="primary", use_container_width=True):
            def split_list(s):
                return [x.strip() for x in s.replace("，", ",").split(",") if x.strip()]
            store.save(type(p)(
                name=name, sex=sex, age=int(age) or None,
                height_cm=height or None, weight_kg=weight or None,
                occupation=occupation, blood_type=blood_type,
                chronic_conditions=split_list(chronic),
                allergies=split_list(allergies),
                medications=split_list(medications),
                family_history=split_list(family),
                lifestyle=Lifestyle(smoking=smoking, drinking=drinking,
                                    exercise=exercise, sleep=sleep, diet=diet),
            ))
            st.toast("档案已保存 ✅")
            st.rerun()


def _render_metrics(get_llm):
    st.markdown("##### 📈 健康指标记录与趋势")
    store = MetricStore()
    metric_keys = list(METRIC_TYPES.keys())
    labels = {k: f"{v[0]}（{v[1]}，参考 {v[2]}）" for k, v in METRIC_TYPES.items()}

    with st.form("metric_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        metric = c1.selectbox("指标", metric_keys, format_func=lambda k: labels[k])
        value = c2.number_input("数值", step=0.1)
        d = c3.date_input("日期", value=date.today())
        note = c4.text_input("备注（可选）", placeholder="如：晨起测量")
        if st.form_submit_button("➕ 添加记录", use_container_width=True):
            if value > 0:
                store.add(metric, value, d.isoformat(), note)
                st.toast("指标已记录 ✅")
                st.rerun()

    df = store.dataframe()
    if df.empty:
        st.info("暂无指标记录。建议每天/每周记录血压、血糖等，数字孪生体会自动分析趋势。")
        return

    # 趋势图
    chart_metric = st.selectbox(
        "选择要查看趋势的指标",
        [k for k in metric_keys if not df[df["metric"] == k].empty],
        format_func=lambda k: labels[k].split("（")[0],
    )
    sub = df[df["metric"] == chart_metric][["date", "value"]].set_index("date")
    st.line_chart(sub, height=260)
    st.dataframe(
        df[df["metric"] == chart_metric].sort_values("date", ascending=False).assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d")),
        use_container_width=True, hide_index=True,
    )


def _render_records():
    st.markdown("##### 📚 历史病历")
    records = list_records()
    if not records:
        st.info("暂无病历。到「AI 智能问诊」完成一次问诊即可自动生成病历。")
        return
    for rec in records:
        with st.expander(f"📄 {rec['title']}（{rec['time']}）"):
            st.markdown(rec["content"])
            if st.button("🗑️ 删除该病历", key=f"delrec_{rec['id']}"):
                delete_record(rec["id"])
                st.rerun()


def render(get_llm, get_kb):
    st.subheader("🧬 数字孪生档案")
    st.caption("你的个人健康数字孪生体：基础档案 + 指标趋势 + 病历，全部本地存储，并作为个性化咨询的数据底座")

    store = ProfileStore()
    p = store.load()
    completeness = p.completeness()
    st.progress(completeness, text=f"档案完整度 {completeness:.0%}（越完整，AI 咨询越个性化）")

    tab1, tab2, tab3, tab4 = st.tabs(["👤 档案", "📈 指标趋势", "📚 病历", "🤖 孪生体评估"])

    with tab1:
        _render_profile_form(store)

    with tab2:
        _render_metrics(get_llm)

    with tab3:
        _render_records()

    with tab4:
        st.caption("基于全部孪生数据（档案 + 指标 + 病历）由 AI 生成综合健康评估：画像、风险分层、干预建议、监测计划")
        if st.button("🤖 生成《数字孪生体健康评估报告》", type="primary", use_container_width=True):
            from agents.twin_analyst import TwinAnalystChain
            with st.spinner("AI 正在分析你的数字孪生体..."):
                try:
                    report = TwinAnalystChain(get_llm(temperature=0.4)).assess()
                except Exception as e:
                    st.error(f"评估失败：{e}\n\n如持续出现，请稍后再试或联系管理员。")
                    st.stop()
            st.session_state.twin_report = report
        if st.session_state.get("twin_report"):
            st.markdown(st.session_state.twin_report)
            st.download_button("📥 下载评估报告", st.session_state.twin_report,
                               file_name="数字孪生体健康评估报告.md", mime="text/markdown")
