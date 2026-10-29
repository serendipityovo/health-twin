"""
全局视觉样式：成熟医疗产品风格
白底 + 医用蓝主色 + 卡片化 + 圆角组件（参考丁香医生 / Apple Health 的产品语言）
"""
import streamlit as st

# ---------------- 设计变量 ----------------
PRIMARY = "#2563EB"      # 医用蓝
PRIMARY_DARK = "#1D4ED8"
NAVY = "#0F2A5C"         # 标题深蓝
TEXT = "#1F2937"
TEXT_LIGHT = "#5B6B84"
BORDER = "#E8EDF4"
SURFACE = "#F7F9FC"

_CSS = f"""
<style>
/* ===================== 基础 ===================== */
html, body, .stApp, [class*="css"] {{
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei UI",
                 "Microsoft YaHei", -apple-system, "Helvetica Neue", Arial, sans-serif;
}}
.stApp {{ background: {SURFACE}; color: {TEXT}; }}
#MainMenu, footer {{ visibility: hidden; }}

header[data-testid="stHeader"] {{
    background: rgba(255, 255, 255, 0.82);
    backdrop-filter: blur(10px);
}}

h1, h2, h3 {{ color: {NAVY}; font-weight: 700; }}
h3 {{ font-size: 1.25rem; }}
a {{ color: {PRIMARY}; }}

/* 细滚动条 */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}

/* ===================== 顶部 Hero ===================== */
.app-hero {{
    position: relative;
    background: linear-gradient(120deg, #E8F1FF 0%, #F6FBFF 55%, #EAF8F5 100%);
    border: 1px solid #D9E7FB;
    border-radius: 18px;
    padding: 24px 28px 20px;
    margin-bottom: 18px;
    overflow: hidden;
}}
.app-hero::after {{
    content: "";
    position: absolute; right: -60px; top: -80px;
    width: 240px; height: 240px; border-radius: 50%;
    background: radial-gradient(circle, rgba(37,99,235,0.10) 0%, transparent 65%);
}}
.hero-title {{
    font-size: 26px; font-weight: 800; color: {NAVY};
    letter-spacing: 0.5px; margin-bottom: 4px;
}}
.hero-sub {{ font-size: 14px; color: {TEXT_LIGHT}; margin-bottom: 12px; }}
.hero-tags {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.hero-tags span {{
    font-size: 12px; font-weight: 600; color: {PRIMARY_DARK};
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid #C9DCF8; border-radius: 999px;
    padding: 3px 12px;
}}

/* ===================== 侧边栏 ===================== */
[data-testid="stSidebar"] {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
/* 导航项卡片化（Streamlit radio，仅限侧边栏导航项） */
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{
    display: flex; align-items: center;
    background: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 11px 14px;
    margin: 5px 0;
    font-weight: 600;
    color: #33415C;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    transition: all 0.15s ease;
    cursor: pointer;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
    border-color: #93C5FD; color: {PRIMARY_DARK};
    transform: translateX(2px);
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{
    background: linear-gradient(90deg, {PRIMARY}, #3B82F6);
    color: #FFFFFF;
    border-color: {PRIMARY};
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28);
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {{
    color: #FFFFFF; font-weight: 700;
}}
/* 隐藏单选圆点 */
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-of-type {{ display: none; }}

/* ===================== 按钮 ===================== */
.stButton > button {{
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid #D7DEE9;
    background: #FFFFFF;
    color: #253651;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    border-color: #60A5FA; color: {PRIMARY_DARK}; background: #F8FAFF;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.12);
}}
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, {PRIMARY}, #3B82F6) !important;
    color: #FFFFFF !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    filter: brightness(1.06);
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.32) !important;
}}

/* ===================== 聊天 ===================== */
[data-testid="stChatMessage"] {{
    background: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 14px 18px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
}}
/* 用户气泡淡蓝，AI 白色 */
[data-testid="stChatMessage"]:has(img[alt="🧑"]) {{
    background: #F0F6FF;
    border-color: #D6E6FF;
}}
[data-testid="stChatInput"] {{
    border-radius: 16px;
}}
[data-testid="stChatInput"] textarea {{
    border-radius: 14px !important;
    border-color: #D7DEE9 !important;
}}

/* ===================== Tabs ===================== */
.stTabs [data-baseweb="tab-list"] {{
    background: #EDF1F7;
    padding: 5px;
    border-radius: 14px;
    gap: 4px;
    width: fit-content;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 10px;
    padding: 7px 16px;
    font-weight: 600;
    color: {TEXT_LIGHT};
}}
.stTabs [data-baseweb="tab"]:hover {{ color: {PRIMARY_DARK}; }}
.stTabs [aria-selected="true"] {{
    background: #FFFFFF;
    color: {PRIMARY_DARK};
    box-shadow: 0 1px 4px rgba(16, 24, 40, 0.10);
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* ===================== 其他组件 ===================== */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER};
    border-radius: 14px;
    background: #FFFFFF;
    overflow: hidden;
}}
[data-testid="stMetric"] {{
    background: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 16px 14px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}}
[data-testid="stMetricValue"] {{ color: {PRIMARY_DARK}; }}
[data-testid="stForm"] {{
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 8px 18px 18px;
    background: #FFFFFF;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    overflow: hidden;
}}
/* 提示条圆角化 */
[data-testid="stAlert"] {{ border-radius: 12px; }}
/* 下载/上传区域 */
[data-testid="stFileUploaderDropzone"] {{
    border-radius: 14px;
    border: 1.5px dashed #C7D6EC;
    background: #FAFCFF;
}}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color: {PRIMARY}; }}
/* 容器卡片（st.container(border=True)） */
[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
}}
</style>
"""


def inject_custom_css():
    """注入全局自定义样式（在 set_page_config 之后调用一次）。"""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_hero():
    """渲染顶部 Hero 横幅，替代默认 st.title。"""
    st.markdown(
        """
        <div class="app-hero">
            <div class="hero-title">🏥 康孪生 HealthTwin</div>
            <div class="hero-sub">基于数字孪生的健康管理系统</div>
            <div class="hero-tags">
                <span>⚡ LangChain 驱动</span>
                <span>🌐 在线 / 离线大模型</span>
                <span>🔒 数据全部本地保存</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
