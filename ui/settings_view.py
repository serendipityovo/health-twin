"""
视图：模型设置 —— 在线 / 离线模型切换、连通性测试、检索状态
"""
from pathlib import Path

import streamlit as st

import config


def _write_env(provider, base_url, model, api_key, emb_base, emb_model):
    """把设置写回 .env（明文保存在本机，仅本地使用）。"""
    lines = [
        f"LLM_PROVIDER={provider}",
        f"ONLINE_BASE_URL={base_url}",
        f"ONLINE_MODEL={model}",
        f"ONLINE_API_KEY={api_key}",
        "OLLAMA_BASE_URL=" + (st.session_state.get("ollama_url", "") or "http://localhost:11434"),
        "OLLAMA_MODEL=" + (st.session_state.get("ollama_model", "") or "qwen2.5:7b"),
        f"EMBEDDING_BASE_URL={emb_base}",
        f"EMBEDDING_MODEL={emb_model}",
    ]
    env_path = config.BASE_DIR / ".env"
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render(get_llm, get_kb):
    st.subheader("⚙️ 模型设置")
    st.caption("支持在线大模型（任意 OpenAI 兼容接口）与离线大模型（Ollama），修改后自动写入 .env 并生效")

    info = config.current_model_info()
    c1, c2 = st.columns(2)
    c1.metric("当前模式", info["provider"])
    c2.metric("当前模型", info["model"])

    st.divider()
    provider = st.radio(
        "切换模型接入方式",
        ["online（在线 API）", "ollama（离线本地）"],
        index=0 if config.LLM_PROVIDER == "online" else 1,
        horizontal=True,
    )

    if provider.startswith("online"):
        st.markdown("##### 在线模型（OpenAI 兼容接口）")
        presets = {
            "智谱 GLM（glm-4-flash 免费额度）": ("https://open.bigmodel.cn/api/paas/v4", "glm-4-flash"),
            "DeepSeek": ("https://api.deepseek.com/v1", "deepseek-chat"),
            "OpenAI": ("https://api.openai.com/v1", "gpt-4o-mini"),
            "原课设 wisediag": ("https://openapi.wisediag.com/v1", "wisediag-large-latest"),
            "自定义": ("", ""),
        }
        preset = st.selectbox("快速预设", list(presets.keys()))
        default_url, default_model = presets[preset]
        base_url = st.text_input("Base URL", value=default_url or config.ONLINE_BASE_URL)
        model = st.text_input("模型名称", value=default_model or config.ONLINE_MODEL)
        api_key = st.text_input("API Key", value=config.ONLINE_API_KEY, type="password")
    else:
        st.markdown("##### 离线模型（Ollama）")
        st.info("先安装 [Ollama](https://ollama.com)，然后执行：`ollama pull qwen2.5:7b`（首次约 4.7GB）")
        st.text_input("Ollama 地址", value=config.OLLAMA_BASE_URL, key="ollama_url")
        st.text_input("模型名称", value=config.OLLAMA_MODEL, key="ollama_model",
                      help="如 qwen2.5:7b / llama3.1:8b / glm4:9b")
        base_url, model, api_key = "", "", ""

    st.markdown("##### 向量检索（可选，留空自动用 BM25 关键词检索）")
    emb_col1, emb_col2 = st.columns(2)
    emb_base = emb_col1.text_input("Embedding Base URL", value=config.EMBEDDING_BASE_URL,
                                   placeholder="如 https://open.bigmodel.cn/api/paas/v4")
    emb_model = emb_col2.text_input("Embedding 模型", value=config.EMBEDDING_MODEL,
                                    placeholder="如 embedding-2")

    if st.button("💾 保存并生效", type="primary", use_container_width=True):
        prov = "ollama" if provider.startswith("ollama") else "online"
        _write_env(prov, base_url, model, api_key, emb_base, emb_model)
        st.cache_resource.clear()
        st.toast("设置已保存 ✅")
        st.rerun()

    st.divider()
    st.markdown("##### 🔌 连通性测试")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("测试大模型", use_container_width=True):
            with st.spinner("调用中..."):
                try:
                    from core.llm import get_chat_model
                    resp = get_chat_model(temperature=0.1).invoke("请只回复两个字：正常")
                    st.success(f"✅ 连通正常，模型回复：{resp.content[:50]}")
                except Exception as e:
                    st.error(f"❌ 调用失败：{e}")
    with col2:
        if st.button("查看 RAG 知识库状态", use_container_width=True):
            kb = get_kb(force_new=True)
            st.info(kb.status())
