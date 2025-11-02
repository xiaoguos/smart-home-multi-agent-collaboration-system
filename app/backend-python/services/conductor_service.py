"""
Conductor Agent 服务
负责与 Conductor Agent 通信
"""

import logging
import httpx
from typing import Dict, Any
from uuid import uuid4

from models.chat import A2ARequest, A2AMessage, A2AMessagePart
from config import settings
from services.chat_history_service import chat_history_service

logger = logging.getLogger(__name__)


class ConductorService:
    """Conductor Agent 通信服务"""
    
    def __init__(self):
        self.base_url = settings.CONDUCTOR_AGENT_URL
        self.timeout = settings.CONDUCTOR_TIMEOUT
        self._request_id_counter = 1
    
    def _generate_message_id(self) -> str:
        """生成消息 ID"""
        return f"msg-{uuid4().hex[:16]}"
    
    def _build_a2a_request(self, user_message: str, system_user_id: int, context_id: str) -> Dict[str, Any]:
        """构建 A2A 协议请求"""
        # 在消息中注入用户ID，让 Agent 知道当前用户
        message_with_user_id = f"[SYSTEM_USER_ID:{system_user_id}] {user_message}"
        
        return {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "context_id": context_id,
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": message_with_user_id
                        }
                    ],
                    "message_id": self._generate_message_id()
                }
            },
            "id": self._request_id_counter
        }
    
    def _extract_content_from_response(self, response: Dict[str, Any]) -> tuple[str, str, bool]:
        """
        从 A2A 响应中提取内容
        
        Returns:
            tuple[str, str, bool]: (content, status, is_error)
                - content: 响应内容
                - status: 状态 (success, failed, error)
                - is_error: 是否为错误
        """
        try:
            result = response.get("result", {})
            
            # 先检查任务状态，如果失败直接返回错误
            status = result.get("status", {})
            state = status.get("state", "")
            
            if state == "failed":
                # 尝试从错误信息中提取详细错误
                error_msg = "❌ 任务执行失败"
                
                # 从history中查找错误信息
                history = result.get("history", [])
                for item in reversed(history):
                    if item.get("role") == "agent":
                        for part in item.get("parts", []):
                            if text := part.get("text"):
                                if "错误" in text or "失败" in text or "error" in text.lower():
                                    error_msg = text
                                    break
                
                return error_msg, "failed", True
            
            # 1. 从 artifacts 提取
            artifacts = result.get("artifacts", [])
            if artifacts:
                contents = []
                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if text := part.get("text"):
                            contents.append(text)
                if contents:
                    return "\n\n".join(contents), "success", False
            
            # 2. 从 history 提取 agent 回复
            history = result.get("history", [])
            agent_messages = []
            for item in history:
                if item.get("role") == "agent":
                    for part in item.get("parts", []):
                        if text := part.get("text"):
                            agent_messages.append(text)
            
            if agent_messages:
                return "\n\n".join(agent_messages), "success", False
            
            # 3. 如果已完成但没有内容
            if state == "completed":
                return "✅ 任务已完成", "success", False
            
            # 4. 默认返回
            return "已收到响应", "success", False
            
        except Exception as e:
            logger.error(f"提取响应内容失败: {e}", exc_info=True)
            return f"处理响应时出错: {str(e)}", "error", True
    
    async def send_message(self, user_message: str, system_user_id: int, context_id: str) -> Dict[str, Any]:
        """
        发送消息到 Conductor Agent
        
        Args:
            user_message: 用户消息
            system_user_id: 系统用户ID
            context_id: 会话上下文ID
            
        Returns:
            包含响应内容的字典
        """
        # 先保存用户消息到数据库
        await chat_history_service.save_message(
            system_user_id=system_user_id,
            context_id=context_id,
            role="user",
            content=user_message,
            status="success"
        )
        
        try:
            # 构建请求（注入用户ID）
            request_data = self._build_a2a_request(user_message, system_user_id, context_id)
            
            logger.info(f"📤 发送消息到 Conductor Agent: {user_message[:50]}...")
            
            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                response_data = response.json()
            
            logger.info(f"📥 收到 Conductor Agent 响应")
            
            # 递增请求ID
            self._request_id_counter += 1
            
            # 提取内容（带错误检测）
            content, msg_status, is_error = self._extract_content_from_response(response_data)
            
            # 提取任务ID和上下文ID
            result = response_data.get("result", {})
            task_id = result.get("id")
            response_context_id = result.get("contextId", context_id)
            
            # 保存agent响应到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=response_context_id,
                role="agent",
                content=content,
                task_id=task_id,
                status=msg_status,
                error_message=content if is_error else None
            )
            
            # 如果是错误，返回错误状态
            if is_error:
                return {
                    "content": content,
                    "context_id": response_context_id,
                    "task_id": task_id,
                    "status": msg_status  # failed 或 error
                }
            
            return {
                "content": content,
                "context_id": response_context_id,
                "task_id": task_id,
                "status": "success"
            }
            
        except httpx.TimeoutException as e:
            error_msg = "⏱️ 请求超时，Agent 可能正在处理复杂任务"
            logger.error(error_msg)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e)
            )
            
            raise Exception(error_msg)
        
        except httpx.ConnectError as e:
            error_msg = f"🔌 无法连接到 Conductor Agent，请确保服务已启动 ({self.base_url})"
            logger.error(error_msg)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e)
            )
            
            raise Exception(error_msg)
        
        except httpx.HTTPStatusError as e:
            error_msg = f"❌ Agent 返回错误: {e.response.status_code}"
            logger.error(error_msg)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e)
            )
            
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"💥 发送消息失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e)
            )
            
            raise Exception(error_msg)
    
    async def test_connection(self) -> bool:
        """测试与 Conductor Agent 的连接"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/.well-known/agent-card.json"
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"✅ Conductor Agent 连接正常: {data.get('name', 'Unknown')}")
                return True
        except Exception as e:
            logger.error(f"❌ Conductor Agent 连接失败: {e}")
            return False


# 创建全局服务实例
conductor_service = ConductorService()

