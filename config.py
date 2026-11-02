"""
康孪生 HealthTwin 全局配置

面向普通用户的版本：模型已写死为 DeepSeek 最新模型（deepseek-chat），
密钥由部署者在 .env / 环境变量 / 打包时内置提供，用户零配置。
（开发者仍可通过 .env 覆盖为其它 OpenAI 兼容接口或 Ollama 离线模式。）

支持 reload() 热更新：设置页保存 .env 后无需重启进程。
"""
import sys
from pathlib import Path

import os
from dotenv import dotenv_values

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

ENV_PATH = BASE_DIR / ".env"


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


def _bypass_proxy_for_deepseek() -> None:
    """DeepSeek 为国内直连服务：显式加入 NO_PROXY，避免系统代理（Clash 等）
    转发时被 TLS 重置导致 "Connection error"（尊重用户已有 NO_PROXY）。"""
    if "deepseek" not in ONLINE_BASE_URL:
        return
    from urllib.parse import urlparse

    host = urlparse(ONLINE_BASE_URL).hostname or "api.deepseek.com"
    existing = os.environ.get("NO_PROXY", os.environ.get("no_proxy", ""))
    entries = [e.strip() for e in existing.split(",") if e.strip()]
    if host not in entries:
        entries.append(host)
    os.environ["NO_PROXY"] = ",".join(entries)
    os.environ["no_proxy"] = os.environ["NO_PROXY"]


def _apply_env() -> None:
    """（重新）加载全部配置项。优先级：系统环境变量 > .env > 内置密钥。"""
    global LLM_PROVIDER, DEEPSEEK_API_KEY, ONLINE_BASE_URL, ONLINE_MODEL
    global OLLAMA_BASE_URL, OLLAMA_MODEL, DEV_MODE
    global TEMPERATURE, MAX_TOKENS, REQUEST_TIMEOUT, RETRIEVER_TOP_K

    file_env: dict = {}
    if ENV_PATH.exists():
        try:
            file_env = {k: v for k, v in (dotenv_values(ENV_PATH) or {}).items() if v is not None}
        except Exception:
            file_env = {}

    def val(key: str, default: str = "") -> str:
        v = os.environ.get(key) or file_env.get(key) or default
        return v.strip() if isinstance(v, str) else str(v).strip()

    DEEPSEEK_API_KEY = val("DEEPSEEK_API_KEY") or _embedded_key()
    ONLINE_BASE_URL = val("ONLINE_BASE_URL", "https://api.deepseek.com/v1")
    ONLINE_MODEL = val("ONLINE_MODEL", "deepseek-chat")
    LLM_PROVIDER = "ollama" if val("LLM_PROVIDER").lower() == "ollama" else "online"
    OLLAMA_BASE_URL = val("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = val("OLLAMA_MODEL", "qwen2.5:7b")
    DEV_MODE = val("DEV_MODE").lower() in ("1", "true", "yes", "on")
    TEMPERATURE = float(val("TEMPERATURE", "0.7") or 0.7)
    MAX_TOKENS = int(val("MAX_TOKENS", "2048") or 2048)
    REQUEST_TIMEOUT = int(val("REQUEST_TIMEOUT", "120") or 120)
    RETRIEVER_TOP_K = int(val("RETRIEVER_TOP_K", "4") or 4)
    _bypass_proxy_for_deepseek()


def reload() -> None:
    """设置页保存 .env 后调用：热更新配置，无需重启进程。"""
    _apply_env()


_apply_env()

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
