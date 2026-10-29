"""
视图：检查报告解读（上传 PDF/TXT 或粘贴文本 → AI 解读 → 自动归档进知识库）
"""
import streamlit as st

from agents.report_reader import ReportReaderChain, extract_pdf_text
from twin.records import delete_report, list_reports


def render(get_llm, get_kb):
    st.subheader("📄 检查报告解读")
    st.caption("上传体检报告 / 化验单（PDF、TXT）或直接粘贴文本，AI 生成专业解读，并自动纳入 RAG 知识库")

    tab_upload, tab_paste = st.tabs(["📤 上传文件", "📋 粘贴文本"])

    content, filename = None, None

    with tab_upload:
        uploaded = st.file_uploader(
            "选择报告文件",
            type=["pdf", "txt", "md"],
            help="PDF 为文本版可直接解析；扫描件无法抽取文字，请改用「粘贴文本」",
        )
        if uploaded is not None:
            if uploaded.name.lower().endswith(".pdf"):
                with st.spinner("正在解析 PDF 文本..."):
                    text = extract_pdf_text(uploaded)
                if text is None:
                    st.error("未能从该 PDF 抽取到文字（可能是扫描件），请改用「粘贴文本」标签页。")
                else:
                    st.success(f"解析成功，共抽取 {len(text)} 字")
                    with st.expander("预览抽取内容"):
                        st.text(text[:1000])
                    content, filename = text, uploaded.name
            else:
                content = uploaded.getvalue().decode("utf-8", errors="ignore")
                filename = uploaded.name

    with tab_paste:
        pasted = st.text_area("粘贴报告内容", height=220, placeholder="把化验单 / 体检报告的文字内容粘贴到这里...")
        if pasted.strip():
            content, filename = pasted.strip(), "粘贴的报告文本"

    if content and st.button("🔍 开始 AI 解读", type="primary", use_container_width=True):
        reader = ReportReaderChain(get_llm(temperature=0.4))
        with st.spinner("AI 正在解读报告..."):
            try:
                result = reader.analyze_and_save(content, filename)
            except Exception as e:
                st.error(f"解读失败：{e}\n\n如持续出现，请稍后再试或联系管理员。")
                st.stop()
        st.session_state.last_report_analysis = result

    if st.session_state.get("last_report_analysis"):
        result = st.session_state.last_report_analysis
        st.divider()
        st.markdown("### 📊 AI 解读结果")
        st.markdown(result["analysis"])
        st.success(f"报告已归档：{result['meta']['title']}（已自动加入 RAG 知识库，咨询时可直接被检索）")

    # ---------------- 历史报告 ----------------
    st.divider()
    st.markdown("#### 🗂️ 历史报告")
    reports = list_reports()
    if not reports:
        st.info("暂无历史报告")
        return
    for rep in reports:
        with st.expander(f"📄 {rep['title']}（{rep['time']}）"):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**报告原文（前500字）**\n\n{rep['content'][:500]}...")
                if rep.get("analysis"):
                    st.markdown(f"**AI 解读（前300字）**\n\n{rep['analysis'][:300]}...")
            with col2:
                st.download_button(
                    "📥 下载原文", data=rep["content"],
                    file_name=f"{rep['id']}.txt", key=f"dl_{rep['id']}",
                )
                if st.button("🗑️ 删除", key=f"del_{rep['id']}"):
                    delete_report(rep["id"])
                    st.rerun()
