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
    
    def _extract_content_from_response(self, response: Dict[str, Any]) -> str:
        """从 A2A 响应中提取内容"""
        try:
            result = response.get("result", {})
            
            # 1. 从 artifacts 提取
            artifacts = result.get("artifacts", [])
            if artifacts:
                contents = []
                for artifact in artifacts:
                    for part in artifact.get("parts", []):
                        if text := part.get("text"):
                            contents.append(text)
                if contents:
                    return "\n\n".join(contents)
            
            # 2. 从 history 提取 agent 回复
            history = result.get("history", [])
            agent_messages = []
            for item in history:
                if item.get("role") == "agent":
                    for part in item.get("parts", []):
                        if text := part.get("text"):
                            agent_messages.append(text)
            
            if agent_messages:
                return "\n\n".join(agent_messages)
            
            # 3. 检查任务状态
            status = result.get("status", {})
            state = status.get("state", "")
            if state == "completed":
                return "✅ 任务已完成"
            elif state == "failed":
                return "❌ 任务执行失败"
            
            # 4. 默认返回
            return "已收到响应"
            
        except Exception as e:
            logger.error(f"提取响应内容失败: {e}", exc_info=True)
            return "处理响应时出错"
    
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
            
            # 提取内容
            content = self._extract_content_from_response(response_data)
            
            # 提取任务ID和上下文ID
            result = response_data.get("result", {})
            task_id = result.get("id")
            response_context_id = result.get("contextId", context_id)
            
            return {
                "content": content,
                "context_id": response_context_id,
                "task_id": task_id,
                "status": "success"
            }
            
        except httpx.TimeoutException:
            logger.error("请求 Conductor Agent 超时")
            raise Exception("请求超时，Agent 可能正在处理复杂任务")
        
        except httpx.ConnectError:
            logger.error(f"无法连接到 Conductor Agent: {self.base_url}")
            raise Exception(f"无法连接到 Conductor Agent，请确保服务已启动 ({self.base_url})")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code}")
            raise Exception(f"Agent 返回错误: {e.response.status_code}")
        
        except Exception as e:
            logger.error(f"发送消息失败: {e}", exc_info=True)
            raise Exception(f"发送消息失败: {str(e)}")
    
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

