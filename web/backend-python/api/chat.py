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
    
    接收前端消息，转发给指定的启用 Agent，返回 AI 回复
    同时将对话记录和设备操作记录存储到数据库
    """
    try:
        # 如果没有提供 context_id，生成一个新的
        context_id = request.context_id or f"session-{uuid4().hex[:16]}"
        
        logger.info(
            "💬 收到聊天请求: %s... (user: %s, context: %s, agent: %s)",
            request.query[:50],
            request.system_user_id,
            context_id,
            request.agent_code,
        )
        
        # 调用目标 Agent（传递用户ID）
        # conductor_service 已经处理了数据库存储逻辑
        result = await conductor_service.send_message(
            user_message=request.query,
            system_user_id=request.system_user_id,
            context_id=context_id,
            agent_code=request.agent_code,
        )
        
        # 构建响应
        response = ChatResponse(
            content=result["content"],
            context_id=result["context_id"],
            task_id=result.get("task_id"),
            status=result["status"],
            agent_code=result.get("agent_code", request.agent_code),
        )
        
        # 根据状态记录不同的日志
        if result["status"] == "success":
            logger.info(f"✅ 聊天响应成功: {len(result['content'])} 字符")
        else:
            logger.warning(f"⚠️ 聊天响应包含错误: status={result['status']}")
        
        return response
        
    except ValueError as e:
        logger.warning(f"⚠️ 聊天请求参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"❌ 聊天请求失败: {e}", exc_info=True)
        # 注意：conductor_service 已经保存了错误到数据库
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

