"""
设备操作记录服务
负责保存和管理设备操作记录
"""
import logging
import time
import random
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from database import insert, query, DatabaseConnectionError

logger = logging.getLogger(__name__)


class DeviceOperationService:
    """设备操作记录服务类"""
    
    @staticmethod
    def save_operation_record(operation_record: Dict[str, Any]) -> bool:
        """
        保存设备操作记录到数据库
        
        Args:
            operation_record: 操作记录字典，包含以下字段：
                - system_user_id: int
                - context_id: Optional[str]
                - device_type: str
                - device_name: Optional[str]
                - action: str
                - parameters: Optional[Dict]
                - success: bool
                - response: Optional[str]
                - error_message: Optional[str]
                - execution_time: Optional[int]
                - timestamp: str (ISO格式)
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 生成操作ID
            op_id = int(time.time() * 1000000) + random.randint(1000, 9999)
            
            # 提取字段
            system_user_id = operation_record.get('system_user_id', 1000000001)
            context_id = operation_record.get('context_id')
            device_type = operation_record.get('device_type')
            device_name = operation_record.get('device_name')
            action = operation_record.get('action')
            parameters = operation_record.get('parameters')
            success = operation_record.get('success', False)
            response = operation_record.get('response')
            error_message = operation_record.get('error_message')
            execution_time = operation_record.get('execution_time')
            
            # 转换参数为JSON
            parameters_json = json.dumps(parameters, ensure_ascii=False) if parameters else None
            
            # SQL插入语句
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
                response[:1000] if response else None,  # 限制长度
                error_message[:500] if error_message else None,  # 限制长度
                execution_time
            )
            
            # 执行插入
            insert(sql, params)
            
            status_emoji = "✅" if success else "❌"
            logger.info(
                f"{status_emoji} 保存设备操作记录: user={system_user_id}, "
                f"device={device_type}, action={action}, success={success}"
            )
            
            return True
            
        except DatabaseConnectionError as e:
            logger.error(f"❌ 数据库连接失败，无法保存操作记录: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 保存设备操作记录失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_recent_operations(
        system_user_id: int,
        limit: int = 50,
        device_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最近的操作记录
        
        Args:
            system_user_id: 用户ID
            limit: 返回记录数量限制
            device_type: 可选，过滤设备类型
        
        Returns:
            操作记录列表
        """
        try:
            if device_type:
                sql = """
                    SELECT * FROM device_operations
                    WHERE system_user_id = %s AND device_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (system_user_id, device_type, limit)
            else:
                sql = """
                    SELECT * FROM device_operations
                    WHERE system_user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (system_user_id, limit)
            
            results = query(sql, params)
            
            # 转换时间戳为字符串
            for record in results:
                if 'created_at' in record and isinstance(record['created_at'], datetime):
                    record['created_at'] = record['created_at'].isoformat()
                
                # 解析parameters JSON
                if 'parameters' in record and record['parameters']:
                    try:
                        record['parameters'] = json.loads(record['parameters'])
                    except:
                        pass
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 查询操作记录失败: {e}")
            return []
    
    @staticmethod
    def get_operation_statistics(
        system_user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取操作统计信息
        
        Args:
            system_user_id: 用户ID
            days: 统计最近多少天
        
        Returns:
            统计信息字典
        """
        try:
            sql = """
                SELECT 
                    device_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as failure_count,
                    AVG(execution_time) as avg_execution_time
                FROM device_operations
                WHERE system_user_id = %s 
                  AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY device_type
            """
            
            results = query(sql, (system_user_id, days))
            
            # 转换结果
            statistics = {
                "period_days": days,
                "devices": {}
            }
            
            for row in results:
                device_type = row['device_type']
                statistics["devices"][device_type] = {
                    "total": int(row['total_count']),
                    "success": int(row['success_count']),
                    "failure": int(row['failure_count']),
                    "success_rate": round(row['success_count'] / row['total_count'] * 100, 2) if row['total_count'] > 0 else 0,
                    "avg_execution_time_ms": round(float(row['avg_execution_time']), 2) if row['avg_execution_time'] else 0
                }
            
            return statistics
            
        except Exception as e:
            logger.error(f"❌ 查询操作统计失败: {e}")
            return {"error": str(e)}


# 全局服务实例
_device_operation_service = None

def get_device_operation_service() -> DeviceOperationService:
    """获取设备操作服务单例"""
    global _device_operation_service
    if _device_operation_service is None:
        _device_operation_service = DeviceOperationService()
    return _device_operation_service
