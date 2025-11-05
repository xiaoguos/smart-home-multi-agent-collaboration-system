"""
对话列表管理服务
负责管理用户的对话列表（会话列表）
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import query, insert, update, get_db_type

logger = logging.getLogger(__name__)


class ConversationService:
    """对话列表管理服务"""
    
    @staticmethod
    def generate_id() -> int:
        """生成唯一ID（使用时间戳+随机数）"""
        import time
        import random
        return int(time.time() * 1000000) + random.randint(1000, 9999)
    
    @staticmethod
    async def create_conversation(
        system_user_id: int,
        context_id: str,
        title: str = "新对话",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新对话
        
        Args:
            system_user_id: 系统用户ID
            context_id: 会话上下文ID
            title: 对话标题
            description: 对话描述（可选）
            
        Returns:
            创建的对话信息
        """
        try:
            conv_id = ConversationService.generate_id()
            
            sql = """
                INSERT INTO conversation_list 
                (id, context_id, system_user_id, title, description, 
                 message_count, created_at, updated_at, is_active)
                VALUES (%s, %s, %s, %s, %s, 0, NOW(), NOW(), TRUE)
            """
            
            params = (conv_id, context_id, system_user_id, title, description)
            
            insert(sql, params)
            logger.info(f"✅ 创建对话成功: user={system_user_id}, context={context_id}, title={title}")
            
            return {
                "id": conv_id,
                "context_id": context_id,
                "system_user_id": system_user_id,
                "title": title,
                "description": description,
                "message_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": True
            }
            
        except Exception as e:
            logger.error(f"❌ 创建对话失败: {e}", exc_info=True)
            raise Exception(f"创建对话失败: {str(e)}")
    
    @staticmethod
    async def get_conversation_by_context(
        context_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据context_id获取对话信息
        
        Args:
            context_id: 会话上下文ID
            
        Returns:
            对话信息，不存在则返回None
        """
        try:
            sql = """
                SELECT id, context_id, system_user_id, title, description, 
                       message_count, last_message, created_at, updated_at, is_active
                FROM conversation_list
                WHERE context_id = %s
                LIMIT 1
            """
            
            results = query(sql, (context_id,))
            
            if results:
                return results[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取对话信息失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def update_conversation(
        context_id: str,
        title: Optional[str] = None,
        last_message: Optional[str] = None,
        increment_message_count: bool = False
    ) -> bool:
        """
        更新对话信息
        
        Args:
            context_id: 会话上下文ID
            title: 新标题（可选）
            last_message: 最后一条消息（可选）
            increment_message_count: 是否增加消息计数
            
        Returns:
            是否成功更新
        """
        try:
            db_type = get_db_type()
            
            # 对于StarRocks，使用DELETE+INSERT策略
            if db_type == 'starrocks':
                # 先获取当前记录
                conv = await ConversationService.get_conversation_by_context(context_id)
                if not conv:
                    logger.warning(f"⚠️ 对话不存在: context={context_id}")
                    return False
                
                # 更新字段
                if title is not None:
                    conv['title'] = title
                if last_message is not None:
                    preview = last_message[:200] if len(last_message) > 200 else last_message
                    conv['last_message'] = preview
                if increment_message_count:
                    conv['message_count'] = conv.get('message_count', 0) + 1
                
                # 删除旧记录
                delete_sql = "DELETE FROM conversation_list WHERE context_id = %s"
                update(delete_sql, (context_id,))
                
                # 插入新记录
                insert_sql = """
                    INSERT INTO conversation_list 
                    (id, system_user_id, updated_at, context_id, title, description, 
                     message_count, last_message, created_at, is_active)
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s)
                """
                insert(insert_sql, (
                    conv['id'],
                    conv['system_user_id'],
                    conv['context_id'],
                    conv['title'],
                    conv.get('description'),
                    conv['message_count'],
                    conv.get('last_message'),
                    conv['created_at'],
                    conv.get('is_active', True)
                ))
                
                logger.info(f"✅ 更新对话成功(StarRocks): context={context_id}")
                return True
            
            # 对于MySQL，使用正常的UPDATE
            else:
                # 构建动态更新SQL
                update_fields = []
                params = []
                
                if title is not None:
                    update_fields.append("title = %s")
                    params.append(title)
                
                if last_message is not None:
                    # 限制预览长度为200字符
                    preview = last_message[:200] if len(last_message) > 200 else last_message
                    update_fields.append("last_message = %s")
                    params.append(preview)
                
                if increment_message_count:
                    update_fields.append("message_count = message_count + 1")
                
                # 总是更新 updated_at
                update_fields.append("updated_at = NOW()")
                
                if not update_fields:
                    return True  # 没有字段需要更新
                
                params.append(context_id)
                
                sql = f"""
                    UPDATE conversation_list 
                    SET {', '.join(update_fields)}
                    WHERE context_id = %s
                """
                
                affected = update(sql, tuple(params))
                
                if affected > 0:
                    logger.info(f"✅ 更新对话成功: context={context_id}")
                    return True
                else:
                    logger.warning(f"⚠️ 对话不存在: context={context_id}")
                    return False
            
        except Exception as e:
            logger.error(f"❌ 更新对话失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_user_conversations(
        system_user_id: int,
        limit: int = 50,
        only_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取用户的对话列表
        
        Args:
            system_user_id: 系统用户ID
            limit: 返回数量限制
            only_active: 是否只返回活跃对话
            
        Returns:
            对话列表（按更新时间倒序）
        """
        try:
            if only_active:
                sql = """
                    SELECT id, context_id, system_user_id, title, description, 
                           message_count, last_message, created_at, updated_at, is_active
                    FROM conversation_list
                    WHERE system_user_id = %s AND is_active = TRUE
                    ORDER BY updated_at DESC
                    LIMIT %s
                """
            else:
                sql = """
                    SELECT id, context_id, system_user_id, title, description, 
                           message_count, last_message, created_at, updated_at, is_active
                    FROM conversation_list
                    WHERE system_user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s
                """
            
            results = query(sql, (system_user_id, limit))
            return results
            
        except Exception as e:
            logger.error(f"❌ 获取对话列表失败: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def delete_conversation(
        context_id: str,
        system_user_id: int,
        soft_delete: bool = True
    ) -> bool:
        """
        删除对话
        
        Args:
            context_id: 会话上下文ID
            system_user_id: 系统用户ID（用于权限验证）
            soft_delete: 是否软删除（仅标记为不活跃）
            
        Returns:
            是否成功删除
        """
        try:
            db_type = get_db_type()
            
            # StarRocks只支持硬删除（DELETE），不支持UPDATE
            if db_type == 'starrocks' or not soft_delete:
                # 硬删除：物理删除记录
                sql = """
                    DELETE FROM conversation_list 
                    WHERE context_id = %s AND system_user_id = %s
                """
                affected = update(sql, (context_id, system_user_id))
                
                if affected > 0:
                    logger.info(f"✅ 删除对话成功: context={context_id}")
                    return True
                else:
                    logger.warning(f"⚠️ 对话不存在或无权限: context={context_id}")
                    return False
            
            # MySQL支持软删除
            else:
                # 软删除：仅标记为不活跃（需要先获取记录再重新插入）
                conv = await ConversationService.get_conversation_by_context(context_id)
                if not conv or conv['system_user_id'] != system_user_id:
                    logger.warning(f"⚠️ 对话不存在或无权限: context={context_id}")
                    return False
                
                # 删除旧记录
                delete_sql = """
                    DELETE FROM conversation_list 
                    WHERE context_id = %s AND system_user_id = %s
                """
                update(delete_sql, (context_id, system_user_id))
                
                # 插入标记为不活跃的记录
                insert_sql = """
                    INSERT INTO conversation_list 
                    (id, system_user_id, updated_at, context_id, title, description, 
                     message_count, last_message, created_at, is_active)
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, FALSE)
                """
                insert(insert_sql, (
                    conv['id'],
                    conv['system_user_id'],
                    conv['context_id'],
                    conv['title'],
                    conv.get('description'),
                    conv['message_count'],
                    conv.get('last_message'),
                    conv['created_at']
                ))
                
                logger.info(f"✅ 软删除对话成功: context={context_id}")
                return True
            
        except Exception as e:
            logger.error(f"❌ 删除对话失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def ensure_conversation_exists(
        system_user_id: int,
        context_id: str,
        title: str = "新对话"
    ) -> Dict[str, Any]:
        """
        确保对话存在，不存在则创建
        
        Args:
            system_user_id: 系统用户ID
            context_id: 会话上下文ID
            title: 对话标题
            
        Returns:
            对话信息
        """
        # 先尝试获取
        conv = await ConversationService.get_conversation_by_context(context_id)
        
        if conv:
            return conv
        
        # 不存在则创建
        return await ConversationService.create_conversation(
            system_user_id=system_user_id,
            context_id=context_id,
            title=title
        )


# 创建全局服务实例
conversation_service = ConversationService()

