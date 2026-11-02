"""
视图：检查报告解读（上传 PDF/TXT 或粘贴文本 → AI 解读 → 自动归档进知识库）
"""
import streamlit as st

from agents.report_reader import ReportReaderChain, extract_pdf_text
from twin.records import delete_report, list_reports


def _decode_text(data: bytes) -> tuple:
    """按 UTF-8 → GB18030（GBK/GB2312 超集）顺序尝试解码，返回 (文本, 编码名)。"""
    for enc in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore"), "utf-8（含无法识别字符）"


def render(get_llm, get_kb):
    st.subheader("📄 检查报告解读")
    st.caption("上传体检报告 / 化验单（PDF、TXT）或直接粘贴文本，AI 生成专业解读，并自动纳入 RAG 知识库")

    tab_upload, tab_paste = st.tabs(["📤 上传文件", "📋 粘贴文本"])

    file_content, file_name = None, None

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
                    file_content, file_name = text, uploaded.name
            else:
                content, enc = _decode_text(uploaded.getvalue())
                if enc != "utf-8-sig":
                    st.caption(f"检测到 {enc} 编码，已自动转换")
                file_content, file_name = content, uploaded.name

    paste_content = None
    with tab_paste:
        pasted = st.text_area("粘贴报告内容", height=220, placeholder="把化验单 / 体检报告的文字内容粘贴到这里...")
        if pasted.strip():
            paste_content = pasted.strip()

    # 优先使用上传文件；两者同时存在时明确告知，避免"粘贴悄悄覆盖上传"
    content, filename = None, None
    if file_content and paste_content:
        st.warning("检测到同时有「上传文件」和「粘贴文本」，将优先使用上传的文件；如想用粘贴内容，请先移除上传的文件。")
        content, filename = file_content, file_name
    elif file_content:
        content, filename = file_content, file_name
    elif paste_content:
        content, filename = paste_content, "粘贴的报告文本"

    if content and st.button("🔍 开始 AI 解读", type="primary", width="stretch"):
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
                if rep.get("analysis"):
                    st.markdown("**AI 解读（完整）**")
                    st.markdown(rep["analysis"])
                st.markdown("**报告原文（完整）**")
                st.text_area(
                    "报告原文（完整）", rep["content"], height=240,
                    disabled=True, key=f"fullsrc_{rep['id']}", label_visibility="collapsed",
                )
            with col2:
                st.download_button(
                    "📥 原文", data=rep["content"],
                    file_name=f"{rep['id']}.txt", key=f"dl_{rep['id']}",
                )
                if rep.get("analysis"):
                    st.download_button(
                        "📥 解读", data=rep["analysis"],
                        file_name=f"{rep['id']}_AI解读.md", key=f"dla_{rep['id']}",
                        mime="text/markdown",
                    )
                if st.button("🗑️ 删除", key=f"del_{rep['id']}"):
                    delete_report(rep["id"])
                    # 同步清掉页面上残留的解读结果
                    last = st.session_state.get("last_report_analysis") or {}
                    if (last.get("meta") or {}).get("id") == rep["id"]:
                        st.session_state.pop("last_report_analysis", None)
                    st.rerun()
