"""
聊天 API 路由
"""

import logging
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from models.chat import ChatRequest, ChatResponse, ErrorResponse
from services.conductor_service import conductor_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口
    
    接收前端消息，转发给 Conductor Agent，返回 AI 回复
    """
    try:
        # 如果没有提供 context_id，生成一个新的
        context_id = request.context_id or f"session-{uuid4().hex[:16]}"
        
        logger.info(f"💬 收到聊天请求: {request.query[:50]}... (context: {context_id})")
        
        # 调用 Conductor Agent
        result = await conductor_service.send_message(
            user_message=request.query,
            context_id=context_id
        )
        
        # 构建响应
        response = ChatResponse(
            content=result["content"],
            context_id=result["context_id"],
            task_id=result.get("task_id"),
            status=result["status"]
        )
        
        logger.info(f"✅ 聊天响应成功: {len(result['content'])} 字符")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ 聊天请求失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ChatError",
                "message": str(e)
            }
        )


@router.get("/chat/health")
async def chat_health():
    """检查聊天服务健康状态"""
    try:
        is_connected = await conductor_service.test_connection()
        
        if is_connected:
            return {
                "status": "healthy",
                "conductor_agent": "connected",
                "url": conductor_service.base_url
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "conductor_agent": "disconnected",
                    "url": conductor_service.base_url
                }
            )
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": str(e)
            }
        )

