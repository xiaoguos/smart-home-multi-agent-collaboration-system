import logging
import httpx
import json
from typing import Dict, Any, Optional
from uuid import uuid4
from urllib.parse import urlparse

from models.chat import A2ARequest, A2AMessage, A2AMessagePart
import env
from database import query
from services.chat_history_service import chat_history_service

logger = logging.getLogger(__name__)


class ConductorService:
    """A2A Agent 通信服务（兼容历史命名）"""
    
    def __init__(self):
        self.base_url = env.CONDUCTOR_AGENT_URL
        self.timeout = env.CONDUCTOR_TIMEOUT
        self._request_id_counter = 1

    @staticmethod
    def _normalize_agent_code(agent_code: Optional[str]) -> str:
        code = (agent_code or "conductor").strip()
        return code or "conductor"

    def _resolve_agent_endpoint(self, agent_code: str) -> tuple[str, str]:
        """
        根据 agent_config 动态解析 Agent 地址，并校验是否启用。

        Returns:
            tuple(base_url, agent_name)
        """
        code = self._normalize_agent_code(agent_code)
        sql = """
            SELECT agent_code, agent_name, host, port, is_enabled
            FROM agent_config
            WHERE agent_code = %s
            LIMIT 1
        """
        rows = query(sql, (code,))

        # 兼容旧配置：如果数据库暂时没有 conductor，则回退到环境变量配置
        if not rows:
            if code == "conductor":
                return self.base_url.rstrip("/"), "Conductor Agent"
            raise ValueError(f"未找到Agent配置: {code}")

        item = rows[0]
        enabled = bool(item.get("is_enabled", False))
        if not enabled:
            raise ValueError(f"Agent已被禁用，无法对话: {code}")

        host = str(item.get("host") or "localhost").strip()
        port = item.get("port")
        agent_name = str(item.get("agent_name") or code)

        if host.startswith("http://") or host.startswith("https://"):
            base_url = host.rstrip("/")
            parsed = urlparse(base_url)
            if port and parsed.port is None:
                base_url = f"{base_url}:{port}"
        else:
            if not port:
                raise ValueError(f"Agent端口未配置: {code}")
            base_url = f"http://{host}:{port}"

        return base_url.rstrip("/"), agent_name
    
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
    
    async def _save_operation_record_if_present(self, content: str, system_user_id: int, context_id: str):
        """
        尝试从响应内容中提取operation_record并保存
        
        如果content中包含JSON格式的operation_record，提取并保存到数据库
        """
        try:
            # 尝试解析content为JSON
            content_json = json.loads(content)
            
            # 检查是否包含operation_record
            if isinstance(content_json, dict) and "operation_record" in content_json:
                operation_record = content_json["operation_record"]
                
                # 更新记录中的用户ID和上下文ID（以确保一致性）
                operation_record["system_user_id"] = system_user_id
                operation_record["context_id"] = context_id
                
                # 导入并使用设备操作服务
                from services.device_operation_service import get_device_operation_service
                device_operation_service = get_device_operation_service()
                
                # 保存操作记录
                success = device_operation_service.save_operation_record(operation_record)
                
                if success:
                    device_type = operation_record.get('device_type', 'unknown')
                    action = operation_record.get('action', 'unknown')
                    logger.info(f"💾 已保存设备操作记录: device={device_type}, action={action}")
                else:
                    logger.warning(f"⚠️ 保存设备操作记录失败")
                    
        except json.JSONDecodeError:
            # content不是JSON格式，跳过
            pass
        except Exception as e:
            logger.error(f"❌ 提取或保存操作记录时出错: {e}", exc_info=True)
    
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
    
    async def send_message(
        self,
        user_message: str,
        system_user_id: int,
        context_id: str,
        agent_code: str = "conductor",
    ) -> Dict[str, Any]:
        """
        发送消息到指定 Agent
        
        Args:
            user_message: 用户消息
            system_user_id: 系统用户ID
            context_id: 会话上下文ID
            
        Returns:
            包含响应内容的字典
        """
        normalized_agent_code = self._normalize_agent_code(agent_code)
        target_base_url, target_agent_name = self._resolve_agent_endpoint(normalized_agent_code)
        metadata = {
            "agent_code": normalized_agent_code,
            "agent_name": target_agent_name,
        }

        # 先保存用户消息到数据库（保存原始用户消息，不带系统前缀）
        await chat_history_service.save_message(
            system_user_id=system_user_id,
            context_id=context_id,
            role="user",
            content=user_message,
            status="success",
            metadata=metadata,
        )
        logger.info(
            "💾 已保存用户消息: context=%s, agent=%s, content=%s...",
            context_id,
            normalized_agent_code,
            user_message[:50],
        )
        
        try:
            # 构建请求（注入用户ID）
            request_data = self._build_a2a_request(user_message, system_user_id, context_id)
            
            logger.info(
                "📤 发送消息到 %s(%s): %s...",
                target_agent_name,
                normalized_agent_code,
                user_message[:50],
            )
            
            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{target_base_url}/",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                response_data = response.json()
            
            logger.info("📥 收到 %s 响应", target_agent_name)
            
            # 递增请求ID
            self._request_id_counter += 1
            
            # 提取内容（带错误检测）
            content, msg_status, is_error = self._extract_content_from_response(response_data)
            
            # 提取任务ID和上下文ID
            result = response_data.get("result", {})
            task_id = result.get("id")
            response_context_id = result.get("contextId", context_id)
            
            # 尝试从content中提取operation_record并保存
            await self._save_operation_record_if_present(content, system_user_id, response_context_id)
            
            # 保存agent响应到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=response_context_id,
                role="agent",
                content=content,
                task_id=task_id,
                status=msg_status,
                error_message=content if is_error else None,
                metadata=metadata,
            )
            logger.info(
                "💾 已保存Agent回复: context=%s, agent=%s, content=%s...",
                response_context_id,
                normalized_agent_code,
                content[:50],
            )
            
            # 如果是错误，返回错误状态
            if is_error:
                return {
                    "content": content,
                    "context_id": response_context_id,
                    "task_id": task_id,
                    "status": msg_status,  # failed 或 error
                    "agent_code": normalized_agent_code,
                }
            
            return {
                "content": content,
                "context_id": response_context_id,
                "task_id": task_id,
                "status": "success",
                "agent_code": normalized_agent_code,
            }
            
        except httpx.TimeoutException as e:
            error_msg = f"⏱️ 请求超时，{target_agent_name} 可能正在处理复杂任务"
            logger.error(error_msg)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e),
                metadata=metadata,
            )
            
            raise Exception(error_msg)
        
        except httpx.ConnectError as e:
            error_msg = f"🔌 无法连接到 {target_agent_name}，请确保服务已启动 ({target_base_url})"
            logger.error(error_msg)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e),
                metadata=metadata,
            )
            
            raise Exception(error_msg)
        
        except httpx.HTTPStatusError as e:
            error_msg = f"❌ {target_agent_name} 返回错误: {e.response.status_code}"
            logger.error(error_msg)
            
            # 保存错误消息到数据库
            await chat_history_service.save_message(
                system_user_id=system_user_id,
                context_id=context_id,
                role="system",
                content=error_msg,
                status="error",
                error_message=str(e),
                metadata=metadata,
            )
            
            raise Exception(error_msg)

        except ValueError:
            # 由上层 API 统一映射为 400 错误
            raise

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
                error_message=str(e),
                metadata=metadata,
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

