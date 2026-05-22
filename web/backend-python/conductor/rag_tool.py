"""
Conductor RAG 工具

提供 query_knowledge_base 工具，让 Conductor Agent 能够在回答问题前
先检索知识库中的相关知识，提升专业知识问答的准确性。
"""

import json
import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KnowledgeQueryArgs(BaseModel):
    query: str = Field(..., description="要查询的问题或关键词")
    top_k: int = Field(default=4, ge=1, le=10, description="返回的相关文档块数量，默认4")
    category: Optional[str] = Field(default=None, description="按分类过滤，如：智能家居、家电说明。不填则全库搜索")


@tool(
    "query_knowledge_base",
    args_schema=KnowledgeQueryArgs,
    description=(
        "查询本地知识库，获取与问题相关的专业知识内容。"
        "适合用于：智能家居操作指南、设备使用说明、家电知识、用户手册等专业问题。"
        "当用户询问设备详细规格、操作步骤、故障排查、保养建议等专业知识时，优先调用此工具。"
    ),
)
def query_knowledge_base(
    query: str,
    top_k: int = 4,
    category: Optional[str] = None,
) -> str:
    """查询知识库，返回相关文档内容"""
    try:
        from rag.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        results = kb.query(query_text=query, top_k=top_k, category=category)

        if not results:
            return json.dumps(
                {"status": "empty", "message": "知识库中暂无相关内容，请根据通用知识回答"},
                ensure_ascii=False,
            )

        # 格式化为 LLM 易读的文本块列表
        formatted_chunks = []
        for i, r in enumerate(results, 1):
            score_label = "高" if r["score"] > 0.8 else ("中" if r["score"] > 0.6 else "低")
            formatted_chunks.append(
                f"【片段{i}】来源：{r['title']}（分类：{r['category']}，相关度：{score_label} {r['score']:.2f}）\n{r['text']}"
            )

        content = "\n\n---\n\n".join(formatted_chunks)
        return json.dumps(
            {
                "status": "success",
                "query": query,
                "found": len(results),
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error("知识库查询工具调用失败: %s", e, exc_info=True)
        return json.dumps(
            {"status": "error", "message": f"知识库暂时不可用: {e}"},
            ensure_ascii=False,
        )
