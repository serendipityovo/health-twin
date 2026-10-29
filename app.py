"""
康孪生 HealthTwin —— 基于数字孪生的健康管理系统
基于 LangChain 框架开发，支持在线大模型 / 离线大模型（Ollama）。

启动：streamlit run app.py
"""
from typing import Optional

import streamlit as st

import config
from core.llm import get_chat_model
from core.retriever import get_knowledge_base

st.set_page_config(
    page_title="康孪生 HealthTwin",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------- 资源缓存（模型 / 知识库） ----------------
@st.cache_resource
def _get_llm_cached(provider: str, key_part: str, temperature: float):
    return get_chat_model(temperature=temperature)


def _config_signature() -> tuple:
    """当前模型配置签名（配置变化时缓存自动失效）。"""
    if config.LLM_PROVIDER == "ollama":
        return ("ollama", config.OLLAMA_MODEL, config.OLLAMA_BASE_URL)
    return ("online", config.ONLINE_MODEL, config.ONLINE_BASE_URL, config.ONLINE_API_KEY[-6:])


def get_llm(temperature: Optional[float] = None):
    """按当前配置获取（缓存的）聊天模型；配置缺失时给出友好提示并停止本页渲染。"""
    temp = config.TEMPERATURE if temperature is None else temperature
    provider, *rest = _config_signature()
    try:
        return _get_llm_cached(provider, "|".join(rest), temp)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.info("请到左侧「⚙️ 模型设置」页配置模型后重试。")
        st.stop()


@st.cache_resource
def _get_kb_cached(signature: tuple):
    kb = get_knowledge_base()
    kb.get_retriever()  # 预热
    return kb


def get_kb(force_new: bool = False):
    if force_new:
        st.cache_resource.clear()
    return _get_kb_cached(_config_signature())


# ---------------- 主界面 ----------------
def main():
    st.title("🏥 康孪生 HealthTwin")
    st.caption("基于数字孪生的健康管理系统 · LangChain 驱动 · 支持在线 / 离线大模型")

    with st.sidebar:
        st.markdown("### 🧭 功能导航")
        page = st.radio(
            "选择功能",
            [
                "💬 智能健康咨询",
                "🧑‍⚕️ AI 智能问诊",
                "📄 检查报告解读",
                "🧬 数字孪生档案",
                "🏥 智能就医匹配",
                "⚙️ 模型设置",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        info = config.current_model_info()
        st.caption(
            f"**模型**：{info['model']}\n\n"
            f"**模式**：{info['provider']}\n\n"
            f"**数据**：全部保存在本地 `data/` 目录"
        )
        if info["provider"].startswith("online") and not config.ONLINE_API_KEY:
            st.warning("尚未配置 API Key，请先到「模型设置」页配置，或切换为 Ollama 离线模式。")

    routes = {
        "💬 智能健康咨询": "ui.consultant_view",
        "🧑‍⚕️ AI 智能问诊": "ui.interview_view",
        "📄 检查报告解读": "ui.report_view",
        "🧬 数字孪生档案": "ui.twin_view",
        "🏥 智能就医匹配": "ui.care_view",
        "⚙️ 模型设置": "ui.settings_view",
    }
    module = __import__(routes[page], fromlist=["render"])
    module.render(get_llm, get_kb)


if __name__ == "__main__":
    main()
