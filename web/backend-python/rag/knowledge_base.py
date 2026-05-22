"""
RAG 知识库核心模块

架构：
  - ChromaDB 持久化向量存储（data/chroma_db/）
  - 嵌入模型：优先使用 DB 配置的 API（OpenAI 兼容），回退到 ChromaDB 内置模型
  - 文本切分：RecursiveCharacterTextSplitter（支持中文）
  - 单例模式，进程内共享同一实例
"""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ChromaDB 数据目录
_CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
_COLLECTION_NAME = "conductor_knowledge"


def _load_ai_config() -> Dict[str, Any]:
    """从数据库加载默认 AI 模型配置（api_key / api_base）。失败则返回空字典。"""
    try:
        from database import query
        rows = query(
            """
            SELECT api_key, api_base
            FROM ai_model_config
            WHERE is_active = 1
            ORDER BY is_default DESC, updated_at DESC
            LIMIT 1
            """,
        )
        if rows:
            return {"api_key": rows[0].get("api_key", ""), "api_base": rows[0].get("api_base", "")}
    except Exception as e:
        logger.debug("加载 AI 配置失败（RAG 回退到内置嵌入）: %s", e)
    return {}


def _build_embedding_function():
    """
    构建嵌入函数，按以下优先级：
    1. 环境变量 EMBEDDING_MODEL + DB 中的 api_key/api_base
    2. ChromaDB 内置模型（onnxruntime，离线可用）
    """
    embedding_model = os.getenv("EMBEDDING_MODEL", "")
    if embedding_model:
        cfg = _load_ai_config()
        api_key = os.getenv("EMBEDDING_API_KEY") or cfg.get("api_key", "")
        api_base = os.getenv("EMBEDDING_API_BASE") or cfg.get("api_base", "")
        if api_key:
            try:
                from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
                logger.info("RAG 使用 OpenAI 兼容嵌入模型: %s @ %s", embedding_model, api_base or "默认")
                return OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name=embedding_model,
                    api_base=api_base if api_base else None,
                )
            except Exception as e:
                logger.warning("OpenAI 嵌入初始化失败，回退到内置模型: %s", e)

    logger.info("RAG 使用 ChromaDB 内置嵌入模型（onnxruntime）")
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    return DefaultEmbeddingFunction()


def _split_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """
    递归字符文本切分，优先在段落/句子边界切分，支持中文。
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
        )
        return splitter.split_text(text)
    except ImportError:
        # 回退：按段落切分
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        chunks: List[str] = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < chunk_size:
                current = (current + "\n\n" + para).lstrip()
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks or [text]


class KnowledgeBase:
    """ChromaDB 知识库封装，进程内单例。"""

    _instance: Optional["KnowledgeBase"] = None

    @classmethod
    def get_instance(cls) -> "KnowledgeBase":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        import chromadb
        self._client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        self._embed_fn = _build_embedding_function()
        self._col = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("✅ RAG 知识库已初始化，当前文档块数: %d", self._col.count())

    # ──────────────────────── 写入 ────────────────────────

    def add_document(
        self,
        title: str,
        content: str,
        category: str = "通用",
        source: str = "",
        doc_id: Optional[str] = None,
    ) -> str:
        """
        切分并写入文档。返回 doc_id。
        """
        doc_id = doc_id or str(uuid.uuid4())
        chunks = _split_text(content)
        if not chunks:
            raise ValueError("文档内容为空，无法写入知识库")

        ids = [f"{doc_id}__{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "title": title,
                "category": category,
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]
        self._col.add(ids=ids, documents=chunks, metadatas=metadatas)
        logger.info("✅ 文档已写入知识库: title=%s, chunks=%d, doc_id=%s", title, len(chunks), doc_id)
        return doc_id

    def delete_document(self, doc_id: str) -> int:
        """删除指定 doc_id 的所有 chunk。返回删除数量。"""
        existing = self._col.get(where={"doc_id": doc_id})
        ids_to_delete = existing.get("ids", [])
        if ids_to_delete:
            self._col.delete(ids=ids_to_delete)
        logger.info("🗑️ 已删除文档 doc_id=%s, 共 %d 块", doc_id, len(ids_to_delete))
        return len(ids_to_delete)

    # ──────────────────────── 查询 ────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量相似搜索。返回 [{text, title, category, score, doc_id, chunk_index}, ...]
        """
        total = self._col.count()
        if total == 0:
            return []

        n = min(top_k, total)
        kwargs: Dict[str, Any] = {"query_texts": [query_text], "n_results": n}
        if category:
            kwargs["where"] = {"category": category}

        results = self._col.query(**kwargs)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        out = []
        for text, meta, dist in zip(docs, metas, dists):
            out.append(
                {
                    "text": text,
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "source": meta.get("source", ""),
                    "doc_id": meta.get("doc_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "score": round(1 - float(dist), 4),  # cosine similarity
                }
            )
        return out

    # ──────────────────────── 管理 ────────────────────────

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        列出所有文档（去重，每个 doc_id 只返回一条摘要）。
        """
        if self._col.count() == 0:
            return []

        results = self._col.get(include=["metadatas", "documents"])
        seen: Dict[str, Dict] = {}
        for meta, doc in zip(results.get("metadatas", []), results.get("documents", [])):
            doc_id = meta.get("doc_id", "")
            if doc_id not in seen:
                seen[doc_id] = {
                    "doc_id": doc_id,
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "source": meta.get("source", ""),
                    "total_chunks": meta.get("total_chunks", 1),
                    "preview": doc[:100] + "..." if len(doc) > 100 else doc,
                }
        return list(seen.values())

    def stats(self) -> Dict[str, Any]:
        """返回知识库统计信息。"""
        docs = self.list_documents()
        categories: Dict[str, int] = {}
        for d in docs:
            cat = d.get("category", "通用")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_chunks": self._col.count(),
            "total_documents": len(docs),
            "categories": categories,
            "chroma_dir": str(_CHROMA_DIR),
        }


def get_knowledge_base() -> KnowledgeBase:
    """获取全局知识库单例（懒初始化，失败时返回 None）。"""
    try:
        return KnowledgeBase.get_instance()
    except Exception as e:
        logger.error("❌ 知识库初始化失败: %s", e)
        raise
