from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# 聊天请求
class ChatRequest(BaseModel):
    query: str = Field(..., description="用户输入的消息")
    system_user_id: int = Field(..., description="系统用户ID（当前登录用户）")
    context_id: Optional[str] = Field(None, description="会话上下文ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "查看所有可用代理",
                "system_user_id": 1000000001,
                "context_id": "session-1234567890"
            }
        }

# 聊天响应
class ChatResponse(BaseModel):
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

# 错误响应
class ErrorResponse(BaseModel):
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")

# A2A 消息部分
class A2AMessagePart(BaseModel):
    kind: str = "text"
    text: str

# A2A 消息
class A2AMessage(BaseModel):
    context_id: str
    role: str = "user"
    parts: List[A2AMessagePart]
    message_id: str

# A2A 请求
class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str = "message/send"
    params: Dict[str, A2AMessage]
    id: int

# A2A 响应
class A2AResponse(BaseModel):
    id: int
    jsonrpc: str
    result: Dict[str, Any]

