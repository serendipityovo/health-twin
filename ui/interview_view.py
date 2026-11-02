"""
视图：AI 智能问诊 → 生成病历 → 数字孪生档案自动同步
"""
import streamlit as st

from agents.interviewer import InterviewChain, KICKOFF
from agents.record_writer import RecordWriterChain


def _stream_doctor_reply(get_llm, dialog, user_input):
    chain = InterviewChain(get_llm(temperature=0.5))
    placeholder = st.empty()
    full = ""
    for chunk in chain.stream_reply(dialog, user_input):
        full += chunk
        placeholder.markdown(full + "▌")
    placeholder.markdown(full)
    return full


def render(get_llm, get_kb):
    st.subheader("🧑‍⚕️ AI 智能问诊")
    st.caption("AI 医生会像真实门诊一样循序渐进地问诊，完成后可一键生成规范病历并同步到数字孪生档案")

    if "interview" not in st.session_state:
        st.session_state.interview = None  # {"dialog": [...], "record_saved": bool}

    # ---------------- 未开始问诊 ----------------
    if st.session_state.interview is None:
        st.info("点击下方按钮开始问诊。AI 医生将依次询问一般信息、主诉、现病史、既往史等，请如实回答。")
        if st.button("▶️ 开始 AI 问诊", type="primary", width="stretch"):
            st.session_state.interview = {"dialog": [], "record_saved": False}
            st.session_state.pop("generated_record", None)
            with st.chat_message("assistant", avatar="🩺"):
                try:
                    reply = _stream_doctor_reply(get_llm, [], KICKOFF)
                except Exception as e:
                    # 启动失败：回退到未开始状态，给出友好提示（不让页面崩掉）
                    st.session_state.interview = None
                    st.error(f"问诊服务启动失败：{e}")
                    st.info("请检查网络后重试；如持续出现请联系管理员。")
                    st.stop()
            st.session_state.interview["dialog"] += [
                {"role": "user", "content": KICKOFF},
                {"role": "assistant", "content": reply},
            ]
            st.rerun()
        return

    interview = st.session_state.interview
    dialog = interview["dialog"]

    # ---------------- 问诊进行中 ----------------
    for m in dialog:
        avatar = "🧑" if m["role"] == "user" else "🩺"
        with st.chat_message("user" if m["role"] == "user" else "assistant", avatar=avatar):
            st.markdown(m["content"])

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        already_saved = interview.get("record_saved", False)
        if st.button(
            "📄 生成病历", type="primary", width="stretch",
            disabled=already_saved,
            help="本次问诊已生成过病历" if already_saved else None,
        ):
            if len(dialog) < 4:
                st.warning("问诊内容太少，请先完成几轮问答再生成病历。")
            else:
                with st.spinner("AI 正在书写规范病历，并同步数字孪生档案..."):
                    writer = RecordWriterChain(get_llm(temperature=0.3))
                    try:
                        result = writer.generate_and_save(dialog)
                    except Exception as e:
                        st.error(f"病历生成失败：{e}")
                        st.stop()
                interview["record_saved"] = True
                st.session_state.generated_record = result
                st.rerun()
    with col2:
        if st.button("🔚 结束问诊", width="stretch"):
            st.session_state.interview = None
            st.session_state.pop("generated_record", None)
            st.rerun()

    if st.session_state.get("generated_record"):
        result = st.session_state.generated_record
        st.divider()
        st.markdown("### 📄 生成的病历")
        st.markdown(result["record"])
        if result.get("extraction") is not None:
            st.success(f"病历已保存：{result['meta']['title']}，并已自动抽取档案信息同步到「数字孪生档案」与 RAG 知识库")
        else:
            st.warning(
                f"病历已保存：{result['meta']['title']}（本次未能自动同步档案，可到「🧬 数字孪生档案」页手动补充）"
            )
        st.download_button(
            "📥 下载病历 (Markdown)",
            data=result["record"],
            file_name=f"{result['meta']['id']}_病历.md",
            mime="text/markdown",
        )
        st.divider()

    if prompt := st.chat_input("请输入你的回答..."):
        dialog.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🩺"):
            try:
                reply = _stream_doctor_reply(get_llm, dialog[:-1], prompt)
            except Exception as e:
                reply = ""
                st.error(f"问诊服务调用失败：{e}")
        if reply:
            dialog.append({"role": "assistant", "content": reply})
