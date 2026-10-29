"""
视图：智能健康咨询（RAG + 数字孪生上下文 + 流式输出）
"""
import streamlit as st

from agents.consultant import ConsultantChain
from twin.context import build_twin_context


def render(get_llm, get_kb):
    st.subheader("💬 智能健康咨询")
    st.caption("结合你的数字孪生档案与历史病历/报告进行个性化检索增强（RAG）问答")

    if "consult_messages" not in st.session_state:
        st.session_state.consult_messages = []

    # 渲染历史
    for m in st.session_state.consult_messages:
        avatar = "🧑" if m["role"] == "user" else "🏥"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])

    kb = get_kb()
    kb_status = kb.status() if kb else "知识库未启用"
    st.caption(f"🔎 检索模式：{kb_status}")

    if prompt := st.chat_input("今天您的身体怎么样？可以问我任何健康问题"):
        st.session_state.consult_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        chain = ConsultantChain(get_llm(), kb)
        with st.chat_message("assistant", avatar="🏥"):
            placeholder = st.empty()
            full = ""
            try:
                for chunk in chain.stream_answer(
                    prompt,
                    st.session_state.consult_messages[:-1],
                    twin_context=build_twin_context(include_records=False),
                ):
                    full += chunk
                    placeholder.markdown(full + "▌")
                placeholder.markdown(full)
            except Exception as e:
                full = f"抱歉，AI 服务调用失败：{e}\n\n如持续出现，请稍后再试或联系管理员。"
                placeholder.markdown(full)
        st.session_state.consult_messages.append({"role": "assistant", "content": full})

    with st.sidebar:
        if st.button("🗑️ 清空当前对话", use_container_width=True):
            st.session_state.consult_messages = []
            st.rerun()
