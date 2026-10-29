"""
视图：🛠 开发者选项（仅 DEV_MODE=1 时出现在导航中）

普通用户界面不出现任何模型 / 密钥 / 供应商概念；
开发者可在此切换自定义模型（任意 OpenAI 兼容 API / Ollama）、
配置密钥并测试连通性。配置写入 .env。
"""
import streamlit as st

import config


def _write_env(fields: dict):
    """合并写入 .env（保留未涉及的键）。"""
    env_path = config.BASE_DIR / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing.update({k: v for k, v in fields.items() if v is not None})
    env_path.write_text(
        "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n", encoding="utf-8"
    )


def render(get_llm, get_kb):
    st.subheader("🛠 开发者选项")
    st.caption("本页仅在 DEV_MODE=1 时可见；普通用户界面不含任何模型配置")

    info = config.current_model_info()
    c1, c2, c3 = st.columns(3)
    c1.metric("当前模型", config.ONLINE_MODEL if config.LLM_PROVIDER == "online" else config.OLLAMA_MODEL)
    c2.metric("接入方式", "在线 API" if config.LLM_PROVIDER == "online" else "Ollama 离线")
    c3.metric("密钥状态", "已配置" if info["key_ready"] else "未配置")

    st.divider()
    provider = st.radio(
        "接入方式",
        ["DeepSeek（默认，写死最新模型）", "自定义 OpenAI 兼容 API", "Ollama 离线模型"],
        horizontal=True,
    )

    fields = {"DEV_MODE": "1"}
    if provider.startswith("DeepSeek"):
        key = st.text_input("DeepSeek API Key（platform.deepseek.com 创建）",
                            value=config.DEEPSEEK_API_KEY, type="password")
        fields.update({"DEEPSEEK_API_KEY": key, "LLM_PROVIDER": "online",
                       "ONLINE_BASE_URL": "https://api.deepseek.com/v1", "ONLINE_MODEL": "deepseek-chat"})
    elif provider.startswith("自定义"):
        base_url = st.text_input("Base URL", value=config.ONLINE_BASE_URL)
        model = st.text_input("模型名称", value=config.ONLINE_MODEL)
        key = st.text_input("API Key", value=config.DEEPSEEK_API_KEY, type="password")
        fields.update({"LLM_PROVIDER": "online", "ONLINE_BASE_URL": base_url,
                       "ONLINE_MODEL": model, "DEEPSEEK_API_KEY": key})
    else:
        st.info("先安装 Ollama 并拉取模型：ollama pull qwen2.5:7b")
        url = st.text_input("Ollama 地址", value=config.OLLAMA_BASE_URL)
        model = st.text_input("模型名称", value=config.OLLAMA_MODEL)
        fields.update({"LLM_PROVIDER": "ollama", "OLLAMA_BASE_URL": url, "OLLAMA_MODEL": model})

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存并生效", type="primary", use_container_width=True):
            _write_env(fields)
            st.cache_resource.clear()
            st.toast("已保存 ✅")
            st.rerun()
    with col2:
        if st.button("🔌 测试连通性", use_container_width=True):
            with st.spinner("调用中..."):
                try:
                    from core.llm import get_chat_model
                    resp = get_chat_model(temperature=0.1).invoke("请只回复两个字：正常")
                    st.success(f"✅ 连通正常，回复：{resp.content[:50]}")
                except Exception as e:
                    st.error(f"❌ 调用失败：{e}")

    with st.expander("🔎 RAG 知识库状态"):
        if st.button("查看 / 重建"):
            kb = get_kb(force_new=True)
            st.info(kb.status())
