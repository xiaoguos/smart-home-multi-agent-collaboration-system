"""
设备操作记录服务
负责存储和查询设备操作记录
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import query, insert

logger = logging.getLogger(__name__)


class DeviceOperationService:
    """设备操作记录服务"""
    
    @staticmethod
    def generate_id() -> int:
        """生成唯一ID（使用时间戳+随机数）"""
        import time
        import random
        return int(time.time() * 1000000) + random.randint(1000, 9999)
    
    @staticmethod
    async def save_operation(
        system_user_id: int,
        device_type: str,
        action: str,
        success: bool,
        context_id: Optional[str] = None,
        device_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        response: Optional[str] = None,
        error_message: Optional[str] = None,
        execution_time: Optional[int] = None
    ) -> bool:
        """
        保存设备操作记录
        
        Args:
            system_user_id: 系统用户ID
            device_type: 设备类型
            action: 操作动作
            success: 是否成功
            context_id: 会话上下文ID（可选）
            device_name: 设备名称（可选）
            parameters: 操作参数（可选）
            response: 操作响应（可选）
            error_message: 错误信息（如果失败）
            execution_time: 执行时间（毫秒）
            
        Returns:
            是否成功保存
        """
        try:
            op_id = DeviceOperationService.generate_id()
            
            # 将参数转为JSON字符串
            parameters_json = json.dumps(parameters, ensure_ascii=False) if parameters else None
            
            sql = """
                INSERT INTO device_operations 
                (id, system_user_id, context_id, device_type, device_name, action, 
                 parameters, success, response, error_message, execution_time, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            params = (
                op_id,
                system_user_id,
                context_id,
                device_type,
                device_name,
                action,
                parameters_json,
                success,
                response,
                error_message,
                execution_time
            )
            
            insert(sql, params)
            
            status_emoji = "✅" if success else "❌"
            logger.info(
                f"{status_emoji} 保存设备操作记录: user={system_user_id}, "
                f"device={device_type}, action={action}, success={success}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存设备操作记录失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_user_operations(
        system_user_id: int,
        device_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取用户的设备操作记录
        
        Args:
            system_user_id: 系统用户ID
            device_type: 设备类型（可选，不指定则返回所有类型）
            limit: 返回记录数量限制
            
        Returns:
            操作记录列表
        """
        try:
            if device_type:
                sql = """
                    SELECT id, system_user_id, context_id, device_type, device_name, 
                           action, parameters, success, response, error_message, 
                           execution_time, created_at
                    FROM device_operations
                    WHERE system_user_id = %s AND device_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (system_user_id, device_type, limit)
            else:
                sql = """
                    SELECT id, system_user_id, context_id, device_type, device_name, 
                           action, parameters, success, response, error_message, 
                           execution_time, created_at
                    FROM device_operations
                    WHERE system_user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (system_user_id, limit)
            
            results = query(sql, params)
            
            # 解析parameters JSON字符串
            for row in results:
                if row.get('parameters'):
                    try:
                        row['parameters'] = json.loads(row['parameters'])
                    except:
                        pass
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 获取设备操作记录失败: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def get_failed_operations(
        system_user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户失败的操作记录
        
        Args:
            system_user_id: 系统用户ID
            limit: 返回记录数量限制
            
        Returns:
            失败的操作记录列表
        """
        try:
            sql = """
                SELECT id, system_user_id, context_id, device_type, device_name, 
                       action, parameters, response, error_message, 
                       execution_time, created_at
                FROM device_operations
                WHERE system_user_id = %s AND success = FALSE
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = query(sql, (system_user_id, limit))
            
            # 解析parameters JSON字符串
            for row in results:
                if row.get('parameters'):
                    try:
                        row['parameters'] = json.loads(row['parameters'])
                    except:
                        pass
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 获取失败操作记录失败: {e}", exc_info=True)
            return []


# 创建全局服务实例
device_operation_service = DeviceOperationService()

