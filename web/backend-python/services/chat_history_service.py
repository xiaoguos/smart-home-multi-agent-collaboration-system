import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import query, insert

logger = logging.getLogger(__name__)

# 延迟导入以避免循环依赖
_conversation_service = None
def get_conversation_service():
    global _conversation_service
    if _conversation_service is None:
        from services.conversation_service import conversation_service
        _conversation_service = conversation_service
    return _conversation_service


class ChatHistoryService:
    """对话记录服务"""
    
    @staticmethod
    def generate_id() -> int:
        """生成唯一ID（使用时间戳+随机数）"""
        import time
        import random
        return int(time.time() * 1000000) + random.randint(1000, 9999)
    
    @staticmethod
    async def save_message(
        system_user_id: int,
        context_id: str,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        task_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        保存对话消息
        
        Args:
            system_user_id: 系统用户ID
            context_id: 会话上下文ID
            role: 角色 (user, agent, system)
            content: 消息内容
            message_id: 消息ID（可选）
            task_id: 任务ID（可选）
            status: 状态 (success, failed, error)
            error_message: 错误信息（如果失败）
            metadata: 元数据（可选）
            
        Returns:
            是否成功保存
        """
        try:
            msg_id = ChatHistoryService.generate_id()
            
            # 将元数据转为JSON字符串
            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
            
            sql = """
                INSERT INTO chat_history 
                (id, system_user_id, context_id, message_id, task_id, role, content, 
                 status, error_message, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            params = (
                msg_id,
                system_user_id,
                context_id,
                message_id,
                task_id,
                role,
                content,
                status,
                error_message,
                metadata_json
            )
            
            insert(sql, params)
            logger.info(f"✅ 保存对话记录成功: user={system_user_id}, role={role}, context={context_id}")
            
            # 更新对话列表
            try:
                conv_service = get_conversation_service()
                
                # 确保对话列表存在
                await conv_service.ensure_conversation_exists(
                    system_user_id=system_user_id,
                    context_id=context_id
                )
                
                # 如果是用户或agent消息，更新最后一条消息和消息计数
                if role in ["user", "agent"]:
                    await conv_service.update_conversation(
                        context_id=context_id,
                        last_message=content,
                        increment_message_count=True
                    )
            except Exception as e:
                logger.warning(f"⚠️ 更新对话列表失败（不影响消息保存）: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存对话记录失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_conversation_history(
        system_user_id: int,
        context_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史记录
        
        Args:
            system_user_id: 系统用户ID
            context_id: 会话上下文ID
            limit: 返回记录数量限制
            
        Returns:
            对话记录列表
        """
        try:
            sql = """
                SELECT id, system_user_id, context_id, message_id, task_id, role, 
                       content, status, error_message, metadata, created_at
                FROM chat_history
                WHERE system_user_id = %s AND context_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = query(sql, (system_user_id, context_id, limit))
            
            # 解析metadata JSON字符串
            for row in results:
                if row.get('metadata'):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except:
                        pass
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 获取会话历史失败: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def get_user_recent_conversations(
        system_user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户最近的对话记录（跨会话）
        
        Args:
            system_user_id: 系统用户ID
            limit: 返回记录数量限制
            
        Returns:
            对话记录列表
        """
        try:
            sql = """
                SELECT id, system_user_id, context_id, message_id, task_id, role, 
                       content, status, error_message, created_at
                FROM chat_history
                WHERE system_user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = query(sql, (system_user_id, limit))
            return results
            
        except Exception as e:
            logger.error(f"❌ 获取用户对话历史失败: {e}", exc_info=True)
            return []


# 创建全局服务实例
chat_history_service = ChatHistoryService()

