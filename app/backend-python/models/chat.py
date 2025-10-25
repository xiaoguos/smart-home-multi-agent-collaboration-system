"""
聊天相关数据模型
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    query: str = Field(..., description="用户输入的消息")
    context_id: Optional[str] = Field(None, description="会话上下文ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "查看所有可用代理",
                "context_id": "session-1234567890"
            }
        }


# ==================== 响应模型 ====================

class ChatResponse(BaseModel):
    """聊天响应"""
    content: str = Field(..., description="AI 回复内容")
    context_id: str = Field(..., description="会话上下文ID")
    task_id: Optional[str] = Field(None, description="任务ID")
    status: str = Field(default="success", description="响应状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "系统中共有 4 个可用代理...",
                "context_id": "session-1234567890",
                "task_id": "task-abc123",
                "status": "success"
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


# ==================== A2A 协议模型 ====================

class A2AMessagePart(BaseModel):
    """A2A 消息部分"""
    kind: str = "text"
    text: str


class A2AMessage(BaseModel):
    """A2A 消息"""
    context_id: str
    role: str = "user"
    parts: List[A2AMessagePart]
    message_id: str


class A2ARequest(BaseModel):
    """A2A 协议请求"""
    jsonrpc: str = "2.0"
    method: str = "message/send"
    params: Dict[str, A2AMessage]
    id: int


class A2AResponse(BaseModel):
    """A2A 协议响应（简化版）"""
    id: int
    jsonrpc: str
    result: Dict[str, Any]

