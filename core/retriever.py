"""
RAG 知识库：把用户的病历、报告、数字孪生档案构建为可检索语料。

检索策略（自动选择）：
  1. 若配置了向量模型（Ollama embeddings 或 OpenAI 兼容 embeddings）→ FAISS 向量检索
  2. 否则自动降级为 BM25 关键词检索（jieba 分词），零外部依赖也可用 RAG
"""
import hashlib
import json
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

import config
from twin.context import build_twin_context
from twin.metrics import MetricStore
from twin.records import list_records, list_reports


def _tokenize_zh(text: str) -> List[str]:
    import jieba
    return [t for t in jieba.lcut(text) if t.strip()]


def _try_build_embeddings():
    """尝试创建向量模型；不可用返回 None（自动降级 BM25）。"""
    try:
        if config.LLM_PROVIDER == "ollama":
            from langchain_ollama import OllamaEmbeddings

            model = config.EMBEDDING_MODEL or "nomic-embed-text"
            emb = OllamaEmbeddings(base_url=config.OLLAMA_BASE_URL, model=model)
            emb.embed_query("连通性测试")
            return emb
        if config.EMBEDDING_BASE_URL and (config.EMBEDDING_API_KEY or config.ONLINE_API_KEY):
            from langchain_openai import OpenAIEmbeddings

            emb = OpenAIEmbeddings(
                base_url=config.EMBEDDING_BASE_URL,
                api_key=config.EMBEDDING_API_KEY or config.ONLINE_API_KEY,
                model=config.EMBEDDING_MODEL or "embedding-2",
                timeout=config.REQUEST_TIMEOUT,
            )
            emb.embed_query("连通性测试")
            return emb
    except Exception:
        return None
    return None


class KnowledgeBase:
    """用户个人健康语料库：文档构建 + 检索器（带签名缓存）。"""

    def __init__(self):
        self._retriever: Optional[BaseRetriever] = None
        self._signature: str = ""
        self._mode: str = ""  # faiss / bm25

    # ---------------- 语料构建 ----------------
    def build_documents(self) -> List[Document]:
        docs: List[Document] = []

        for rec in list_records():
            docs.append(Document(
                page_content=rec["content"],
                metadata={"source": "medical_record", "id": rec["id"], "time": rec["time"]},
            ))
        for rep in list_reports():
            docs.append(Document(
                page_content=rep["content"],
                metadata={"source": "health_report", "id": rep["id"], "time": rep["time"]},
            ))

        # 数字孪生档案（含指标趋势摘要）整体作为一份文档
        twin_ctx = build_twin_context(include_records=False)
        if twin_ctx.strip() and twin_ctx != "（暂无档案数据）":
            docs.append(Document(page_content=twin_ctx, metadata={"source": "twin_profile"}))
        return docs

    # ---------------- 检索器 ----------------
    @staticmethod
    def _signature_of(docs: List[Document]) -> str:
        raw = json.dumps(
            [[d.metadata.get("id", ""), d.metadata.get("time", ""), len(d.page_content)] for d in docs],
            ensure_ascii=False,
        )
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get_retriever(self, force_rebuild: bool = False) -> Optional[BaseRetriever]:
        docs = self.build_documents()
        if not docs:
            self._retriever = None
            self._mode = "empty"
            return None

        sig = self._signature_of(docs)
        if not force_rebuild and self._retriever is not None and sig == self._signature:
            return self._retriever

        # 1) 优先 FAISS 向量检索
        embeddings = _try_build_embeddings()
        if embeddings is not None:
            try:
                from langchain_community.vectorstores import FAISS

                vs = FAISS.from_documents(docs, embeddings)
                self._retriever = vs.as_retriever(search_kwargs={"k": config.RETRIEVER_TOP_K})
                self._mode = f"FAISS 向量检索（{embeddings.__class__.__name__}）"
                self._signature = sig
                return self._retriever
            except Exception:
                pass

        # 2) 降级 BM25
        from langchain_community.retrievers import BM25Retriever

        bm25 = BM25Retriever.from_documents(docs, preprocess_func=_tokenize_zh)
        bm25.k = config.RETRIEVER_TOP_K
        self._retriever = bm25
        self._mode = "BM25 关键词检索（jieba 分词，自动降级模式）"
        self._signature = sig
        return self._retriever

    def search(self, query: str) -> List[Document]:
        retriever = self.get_retriever()
        if retriever is None:
            return []
        try:
            return retriever.invoke(query)
        except Exception:
            return []

    def status(self) -> str:
        if self._mode == "empty":
            return "知识库为空（暂无病历 / 报告 / 档案数据）"
        if not self._mode:
            self.get_retriever()
        n = len(self.build_documents())
        return f"{self._mode}，当前语料 {n} 份文档"


# 模块级单例（Streamlit 中配合 st.cache_resource 使用）
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()
