import logging
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional

from pydantic import BaseModel, Field
from services.conversation_service import conversation_service
from services.chat_history_service import chat_history_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 请求/响应模型 ====================

class CreateConversationRequest(BaseModel):
    system_user_id: int = Field(..., description="系统用户ID")
    title: str = Field(default="新对话", description="对话标题")
    description: Optional[str] = Field(None, description="对话描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "system_user_id": 1000000001,
                "title": "智能家居控制",
                "description": "关于空调和灯光的对话"
            }
        }


class UpdateConversationRequest(BaseModel):
    context_id: str = Field(..., description="会话上下文ID")
    title: Optional[str] = Field(None, description="新标题")
    
    class Config:
        json_schema_extra = {
            "example": {
                "context_id": "session-abc123",
                "title": "空调温度调节"
            }
        }


class DeleteConversationRequest(BaseModel):
    context_id: str = Field(..., description="会话上下文ID")
    system_user_id: int = Field(..., description="系统用户ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "context_id": "session-abc123",
                "system_user_id": 1000000001
            }
        }


# ==================== API 端点 ====================

@router.post("/conversations/create")
async def create_conversation(request: CreateConversationRequest):
    """
    创建新对话
    """
    try:
        # 生成新的 context_id
        context_id = f"session-{uuid4().hex[:16]}"
        
        logger.info(f"📝 创建新对话: user={request.system_user_id}, title={request.title}")
        
        conversation = await conversation_service.create_conversation(
            system_user_id=request.system_user_id,
            context_id=context_id,
            title=request.title,
            description=request.description
        )
        
        logger.info(f"✅ 创建对话成功: context={context_id}")
        
        return {
            "success": True,
            "message": "创建对话成功",
            "data": conversation
        }
        
    except Exception as e:
        logger.error(f"❌ 创建对话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CreateConversationError",
                "message": str(e)
            }
        )


@router.get("/conversations/list")
async def get_conversations(
    system_user_id: int = Query(..., description="系统用户ID"),
    limit: int = Query(50, description="返回数量限制"),
    only_active: bool = Query(True, description="是否只返回活跃对话")
):
    """
    获取用户的对话列表
    """
    try:
        logger.info(f"📋 获取对话列表: user={system_user_id}, limit={limit}")
        
        conversations = await conversation_service.get_user_conversations(
            system_user_id=system_user_id,
            limit=limit,
            only_active=only_active
        )
        
        return {
            "success": True,
            "message": "获取对话列表成功",
            "data": conversations,
            "total": len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GetConversationsError",
                "message": str(e)
            }
        )


@router.get("/conversations/{context_id}")
async def get_conversation(context_id: str):
    """
    获取指定对话的详细信息
    """
    try:
        logger.info(f"🔍 获取对话详情: context={context_id}")
        
        conversation = await conversation_service.get_conversation_by_context(context_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ConversationNotFound",
                    "message": f"对话不存在: {context_id}"
                }
            )
        
        return {
            "success": True,
            "message": "获取对话详情成功",
            "data": conversation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GetConversationError",
                "message": str(e)
            }
        )


@router.put("/conversations/update")
async def update_conversation(request: UpdateConversationRequest):
    """
    更新对话信息（如标题）
    """
    try:
        success = await conversation_service.update_conversation(
            context_id=request.context_id,
            title=request.title
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ConversationNotFound",
                    "message": f"对话不存在: {request.context_id}"
                }
            )
        
        return {
            "success": True,
            "message": "更新对话成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "UpdateConversationError",
                "message": str(e)
            }
        )


@router.delete("/conversations/delete")
async def delete_conversation(request: DeleteConversationRequest):
    """
    删除对话（软删除）
    """
    try:
        success = await conversation_service.delete_conversation(
            context_id=request.context_id,
            system_user_id=request.system_user_id,
            soft_delete=True
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ConversationNotFound",
                    "message": f"对话不存在或无权限: {request.context_id}"
                }
            )
        
        return {
            "success": True,
            "message": "删除对话成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DeleteConversationError",
                "message": str(e)
            }
        )


@router.get("/conversations/{context_id}/history")
async def get_conversation_history(
    context_id: str,
    system_user_id: int = Query(..., description="系统用户ID"),
    limit: int = Query(50, description="返回消息数量限制")
):
    """
    获取指定对话的历史消息
    """
    try:
        logger.info(f"📜 获取对话历史: context={context_id}, limit={limit}")
        
        messages = await chat_history_service.get_conversation_history(
            system_user_id=system_user_id,
            context_id=context_id,
            limit=limit
        )
        
        # 确保是列表，然后反转顺序，使得最旧的消息在前
        messages = list(messages) if not isinstance(messages, list) else messages
        messages.reverse()
        
        return {
            "success": True,
            "message": "获取对话历史成功",
            "data": messages,
            "total": len(messages)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GetConversationHistoryError",
                "message": str(e)
            }
        )

