"""
康孪生 HealthTwin 全局配置

支持两种模型接入方式（在 .env 或「模型设置」页面中配置）：
  1. online : 任意 OpenAI 兼容在线大模型（智谱 GLM / DeepSeek / wisediag / OpenAI ...）
  2. ollama : 本地离线大模型（Ollama，如 qwen2.5 / llama3 / glm4 ...）
"""
from pathlib import Path

import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------------
# 大模型提供商：online（在线 API） / ollama（离线本地模型）
# ------------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "online").strip().lower()

# ---- 在线：OpenAI 兼容接口（默认智谱 GLM，glm-4-flash 免费额度） ----
ONLINE_BASE_URL = os.getenv("ONLINE_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
ONLINE_API_KEY = os.getenv("ONLINE_API_KEY", "")
ONLINE_MODEL = os.getenv("ONLINE_MODEL", "glm-4-flash")

# ---- 离线：Ollama 本地模型 ----
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# ------------------------------------------------------------------
# 向量检索（RAG）配置：可选。
# 留空时系统自动降级为 BM25 关键词检索，保证任何环境都能用 RAG。
# ------------------------------------------------------------------
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")

# ------------------------------------------------------------------
# 生成参数
# ------------------------------------------------------------------
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))

# RAG 检索条数
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "4"))

# ------------------------------------------------------------------
# 数据目录（数字孪生档案、指标、病历、报告、向量索引，全部保存在本地）
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
    """返回当前生效的模型配置摘要（用于设置页展示）。"""
    if LLM_PROVIDER == "ollama":
        return {
            "provider": "ollama（离线本地模型）",
            "base_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
            "api_key": "（本地模型无需密钥）",
        }
    return {
        "provider": "online（在线 OpenAI 兼容模型）",
        "base_url": ONLINE_BASE_URL,
        "model": ONLINE_MODEL,
        "api_key": (ONLINE_API_KEY[:6] + "..." + ONLINE_API_KEY[-4:]) if len(ONLINE_API_KEY) > 12 else ("已配置" if ONLINE_API_KEY else "未配置"),
    }
