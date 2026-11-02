"""
康孪生 HealthTwin 全局配置

面向普通用户的版本：模型已写死为 DeepSeek 最新模型（deepseek-chat），
密钥由部署者在 .env / 环境变量 / 打包时内置提供，用户零配置。
（开发者仍可通过 .env 覆盖为其它 OpenAI 兼容接口或 Ollama 离线模式。）
"""
import sys
from pathlib import Path

import os
from dotenv import load_dotenv

# ------------------------------------------------------------------
# 运行形态：源码运行 vs PyInstaller 打包（exe）运行
#   打包后：资源（代码/知识库）在 exe 的 _internal 目录，用户数据在 exe 旁边
# ------------------------------------------------------------------
IS_FROZEN = bool(getattr(sys, "frozen", False))
if IS_FROZEN:
    BASE_DIR = Path(sys.executable).resolve().parent       # exe 旁：data/、.env
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))  # 打包资源：knowledge 等
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

load_dotenv(BASE_DIR / ".env")


def _embedded_key() -> str:
    """构建时烧录进发行版的密钥（packaging/_embedded_key.py），最后才回退到它。"""
    try:
        from importlib import util
        spec = util.find_spec("_embedded_key")
        if spec and spec.loader:
            module = util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return str(getattr(module, "DEEPSEEK_API_KEY", "") or "")
    except Exception:
        pass
    return ""

# ------------------------------------------------------------------
# 模型：DeepSeek（写死，deepseek-chat 始终指向 DeepSeek 最新 V3 系列）
# 密钥优先级：系统环境变量 > .env > 打包时内置
# ------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip() or _embedded_key()
ONLINE_BASE_URL = os.getenv("ONLINE_BASE_URL", "https://api.deepseek.com/v1")
ONLINE_MODEL = os.getenv("ONLINE_MODEL", "deepseek-chat")

# 开发者模式：true 时导航出现「🛠 开发者选项」页（自定义模型/密钥/连通性测试）
DEV_MODE = os.getenv("DEV_MODE", "").strip().lower() in ("1", "true", "yes", "on")

# 开发者高级选项（默认关闭）：ollama = 离线本地模型
LLM_PROVIDER = "ollama" if os.getenv("LLM_PROVIDER", "").strip().lower() == "ollama" else "online"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# ------------------------------------------------------------------
# 生成参数
# ------------------------------------------------------------------
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))

# RAG 检索条数
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "4"))

# ------------------------------------------------------------------
# 数据目录（数字孪生档案、指标、病历、报告，全部保存在本地）
# ------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
METRICS_PATH = DATA_DIR / "metrics.json"
RECORDS_DIR = DATA_DIR / "records"
REPORTS_DIR = DATA_DIR / "reports"
INDEX_DIR = DATA_DIR / "faiss_index"
KNOWLEDGE_DIR = RESOURCE_DIR / "knowledge"

for _d in (DATA_DIR, RECORDS_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def current_model_info() -> dict:
    """返回当前模型状态摘要（用于侧边栏 / 开发者页展示）。"""
    return {
        "model": "DeepSeek（内置，无需配置）",
        "key_ready": bool(DEEPSEEK_API_KEY) or LLM_PROVIDER == "ollama",
        "dev_mode": DEV_MODE,
    }
