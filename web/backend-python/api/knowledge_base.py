"""
知识库管理 API

端点：
  POST   /knowledge-base/documents        添加文本文档
  POST   /knowledge-base/upload           上传文件（txt / md）
  GET    /knowledge-base/documents        列出所有文档
  DELETE /knowledge-base/documents/{id}  删除文档
  POST   /knowledge-base/query           测试查询
  GET    /knowledge-base/stats           统计信息
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


# ──────────────── 请求 / 响应模型 ────────────────

class AddDocumentRequest(BaseModel):
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容（纯文本）")
    category: str = Field(default="通用", description="分类，如：智能家居、家电说明、操作手册等")
    source: str = Field(default="", description="来源说明（可选）")


class QueryRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    category: Optional[str] = Field(default=None, description="按分类过滤（可选）")


# ──────────────── 路由 ────────────────

@router.post("/documents")
async def add_document(req: AddDocumentRequest):
    """添加文本文档到知识库"""
    from rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        doc_id = kb.add_document(
            title=req.title,
            content=req.content,
            category=req.category,
            source=req.source,
        )
        return {"status": "success", "doc_id": doc_id, "message": f"文档「{req.title}」已写入知识库"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("写入知识库失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = "通用",
    source: str = "",
):
    """上传文件（支持 .txt / .md）写入知识库"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("txt", "md"):
        raise HTTPException(status_code=400, detail="仅支持 .txt / .md 文件")

    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("gbk", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    from rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        title = file.filename.rsplit(".", 1)[0]
        doc_id = kb.add_document(title=title, content=content, category=category, source=source or file.filename)
        return {"status": "success", "doc_id": doc_id, "filename": file.filename, "message": f"文件「{file.filename}」已写入知识库"}
    except Exception as e:
        logger.error("上传文件写入知识库失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")


@router.get("/documents")
async def list_documents():
    """列出知识库中所有文档"""
    from rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        docs = kb.list_documents()
        return {"status": "success", "total": len(docs), "documents": docs}
    except Exception as e:
        logger.error("列出知识库文档失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除指定文档（按 doc_id）"""
    from rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        count = kb.delete_document(doc_id)
        if count == 0:
            raise HTTPException(status_code=404, detail=f"未找到 doc_id={doc_id} 的文档")
        return {"status": "success", "doc_id": doc_id, "deleted_chunks": count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除知识库文档失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


@router.post("/query")
async def query_knowledge_base(req: QueryRequest):
    """测试查询知识库（返回相关文本块）"""
    from rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        results = kb.query(query_text=req.query, top_k=req.top_k, category=req.category)
        return {"status": "success", "query": req.query, "results": results}
    except Exception as e:
        logger.error("知识库查询失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.get("/stats")
async def get_stats():
    """获取知识库统计信息"""
    from rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        return {"status": "success", **kb.stats()}
    except Exception as e:
        logger.error("获取知识库统计失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计失败: {e}")
