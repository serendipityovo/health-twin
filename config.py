"""
康孪生 HealthTwin 全局配置

面向普通用户的版本：模型已写死为 DeepSeek 最新模型（deepseek-chat），
用户只需粘贴一次 API Key 即可使用，无需任何模型知识。
（开发者仍可通过 .env 覆盖为其它 OpenAI 兼容接口或 Ollama 离线模式。）
"""
from pathlib import Path

import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------------
# 模型：DeepSeek（写死，deepseek-chat 始终指向 DeepSeek 最新 V3 系列）
# 密钥由部署者在 .env 中预置，普通用户界面不出现任何模型/密钥概念。
# ------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
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
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

for _d in (DATA_DIR, RECORDS_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def current_model_info() -> dict:
    """返回当前模型状态摘要（用于侧边栏 / 开发者页展示）。"""
    return {
        "model": "DeepSeek（内置，无需配置）",
        "key_ready": bool(DEEPSEEK_API_KEY) or LLM_PROVIDER == "ollama",
        "dev_mode": DEV_MODE,
    }
