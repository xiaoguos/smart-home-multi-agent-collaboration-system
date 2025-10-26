"""
配置管理服务
从数据库中读取和更新系统配置
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigService:
    """配置管理服务类"""
    
    def __init__(self, db_connection):
        """
        初始化配置服务
        
        Args:
            db_connection: 数据库连接实例
        """
        self.db = db_connection
    
    # ==================== AI 模型配置 ====================
    
    def get_ai_models(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        获取AI模型配置列表
        
        Args:
            is_active: 是否只获取激活的模型
            
        Returns:
            AI模型配置列表
        """
        sql = "SELECT * FROM ai_model_config"
        params = None
        
        if is_active is not None:
            sql += " WHERE is_active = %s"
            params = (is_active,)
        
        sql += " ORDER BY is_default DESC, id ASC"
        return self.db.execute_query(sql, params)
    
    def get_default_ai_model(self) -> Optional[Dict[str, Any]]:
        """获取默认AI模型配置"""
        sql = "SELECT * FROM ai_model_config WHERE is_default = TRUE AND is_active = TRUE LIMIT 1"
        results = self.db.execute_query(sql)
        return results[0] if results else None
    
    def get_ai_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取AI模型配置"""
        sql = "SELECT * FROM ai_model_config WHERE id = %s"
        results = self.db.execute_query(sql, (model_id,))
        return results[0] if results else None
    
    def update_ai_model(self, model_id: int, data: Dict[str, Any]) -> bool:
        """
        更新AI模型配置
        
        Args:
            model_id: 模型ID
            data: 更新数据
            
        Returns:
            是否更新成功
        """
        allowed_fields = ['model_name', 'provider', 'api_key', 'api_base', 
                         'model_type', 'temperature', 'max_tokens', 'is_default', 'is_active']
        
        updates = []
        params = []
        
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        params.append(model_id)
        
        sql = f"UPDATE ai_model_config SET {', '.join(updates)} WHERE id = %s"
        affected = self.db.execute_update(sql, tuple(params))
        return affected > 0
    
    def create_ai_model(self, data: Dict[str, Any]) -> int:
        """
        创建新的AI模型配置
        
        Args:
            data: 模型配置数据
            
        Returns:
            新创建的模型ID
        """
        required_fields = ['model_name', 'provider', 'api_key', 'api_base']
        
        # 验证必填字段
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必填字段: {field}")
        
        sql = """
            INSERT INTO ai_model_config 
            (model_name, provider, api_key, api_base, model_type, temperature, max_tokens, is_default, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['model_name'],
            data['provider'],
            data['api_key'],
            data['api_base'],
            data.get('model_type', 'chat'),
            data.get('temperature', 0.7),
            data.get('max_tokens', 2048),
            data.get('is_default', False),
            data.get('is_active', True)
        )
        
        self.db.execute_update(sql, params)
        # 获取最后插入的ID
        result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
        return result[0]['id'] if result else 0
    
    # ==================== Agent 配置 ====================
    
    def get_agents(self, is_enabled: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        获取Agent配置列表
        
        Args:
            is_enabled: 是否只获取启用的Agent
            
        Returns:
            Agent配置列表
        """
        sql = "SELECT * FROM agent_config"
        params = None
        
        if is_enabled is not None:
            sql += " WHERE is_enabled = %s"
            params = (is_enabled,)
        
        sql += " ORDER BY id ASC"
        return self.db.execute_query(sql, params)
    
    def get_agent_by_code(self, agent_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取Agent配置"""
        sql = "SELECT * FROM agent_config WHERE agent_code = %s"
        results = self.db.execute_query(sql, (agent_code,))
        return results[0] if results else None
    
    def update_agent(self, agent_id: int, data: Dict[str, Any]) -> bool:
        """更新Agent配置"""
        allowed_fields = ['agent_name', 'host', 'port', 'description', 'is_enabled']
        
        updates = []
        params = []
        
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        params.append(agent_id)
        
        sql = f"UPDATE agent_config SET {', '.join(updates)} WHERE id = %s"
        affected = self.db.execute_update(sql, tuple(params))
        return affected > 0
    
    # ==================== Agent 提示词 ====================
    
    def get_agent_prompt(self, agent_code: str) -> Optional[str]:
        """
        获取Agent的系统提示词
        
        Args:
            agent_code: Agent代码
            
        Returns:
            系统提示词文本
        """
        sql = "SELECT prompt_text FROM agent_prompt WHERE agent_code = %s AND is_active = TRUE ORDER BY id DESC LIMIT 1"
        results = self.db.execute_query(sql, (agent_code,))
        return results[0]['prompt_text'] if results else None
    
    def update_agent_prompt(self, agent_code: str, prompt_text: str, version: str = 'v1.0') -> bool:
        """
        更新Agent的系统提示词
        
        Args:
            agent_code: Agent代码
            prompt_text: 提示词文本
            version: 版本号
            
        Returns:
            是否更新成功
        """
        # 先将旧的提示词设为非激活
        sql_deactivate = "UPDATE agent_prompt SET is_active = FALSE WHERE agent_code = %s"
        self.db.execute_update(sql_deactivate, (agent_code,))
        
        # 插入新的提示词
        sql_insert = """
            INSERT INTO agent_prompt (agent_code, prompt_text, version, is_active)
            VALUES (%s, %s, %s, TRUE)
        """
        affected = self.db.execute_update(sql_insert, (agent_code, prompt_text, version))
        return affected > 0
    
    # ==================== 设备配置 ====================
    
    def get_devices(self, device_type: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        获取设备配置列表
        
        Args:
            device_type: 设备类型
            is_active: 是否只获取激活的设备
            
        Returns:
            设备配置列表
        """
        sql = "SELECT * FROM device_config WHERE 1=1"
        params = []
        
        if device_type:
            sql += " AND device_type = %s"
            params.append(device_type)
        
        if is_active is not None:
            sql += " AND is_active = %s"
            params.append(is_active)
        
        sql += " ORDER BY id ASC"
        return self.db.execute_query(sql, tuple(params) if params else None)
    
    def get_device_by_code(self, device_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取设备配置"""
        sql = "SELECT * FROM device_config WHERE device_code = %s"
        results = self.db.execute_query(sql, (device_code,))
        return results[0] if results else None
    
    def update_device(self, device_id: int, data: Dict[str, Any]) -> bool:
        """更新设备配置"""
        allowed_fields = ['device_name', 'ip_address', 'token', 'model', 'extra_config', 'is_active']
        
        updates = []
        params = []
        
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        params.append(device_id)
        
        sql = f"UPDATE device_config SET {', '.join(updates)} WHERE id = %s"
        affected = self.db.execute_update(sql, tuple(params))
        return affected > 0
    
    def create_device(self, data: Dict[str, Any]) -> int:
        """创建新设备配置"""
        required_fields = ['device_code', 'device_name', 'device_type', 'agent_code']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必填字段: {field}")
        
        sql = """
            INSERT INTO device_config 
            (device_code, device_name, device_type, agent_code, ip_address, token, model, extra_config, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['device_code'],
            data['device_name'],
            data['device_type'],
            data['agent_code'],
            data.get('ip_address'),
            data.get('token'),
            data.get('model'),
            data.get('extra_config'),
            data.get('is_active', True)
        )
        
        self.db.execute_update(sql, params)
        result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
        return result[0]['id'] if result else 0
    
    # ==================== 小米账号配置 ====================
    
    def get_xiaomi_accounts(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """获取小米账号配置列表"""
        sql = "SELECT * FROM xiaomi_account"
        params = None
        
        if is_active is not None:
            sql += " WHERE is_active = %s"
            params = (is_active,)
        
        sql += " ORDER BY is_default DESC, id ASC"
        return self.db.execute_query(sql, params)
    
    def get_default_xiaomi_account(self) -> Optional[Dict[str, Any]]:
        """获取默认小米账号"""
        sql = "SELECT * FROM xiaomi_account WHERE is_default = TRUE AND is_active = TRUE LIMIT 1"
        results = self.db.execute_query(sql)
        return results[0] if results else None
    
    def update_xiaomi_account(self, account_id: int, data: Dict[str, Any]) -> bool:
        """更新小米账号配置"""
        allowed_fields = ['username', 'password', 'region', 'is_default', 'is_active']
        
        updates = []
        params = []
        
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        params.append(account_id)
        
        sql = f"UPDATE xiaomi_account SET {', '.join(updates)} WHERE id = %s"
        affected = self.db.execute_update(sql, tuple(params))
        return affected > 0
    
    def create_xiaomi_account(self, data: Dict[str, Any]) -> int:
        """创建新小米账号配置"""
        required_fields = ['username', 'password']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必填字段: {field}")
        
        sql = """
            INSERT INTO xiaomi_account 
            (username, password, region, is_default, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            data['username'],
            data['password'],
            data.get('region', 'cn'),
            data.get('is_default', False),
            data.get('is_active', True)
        )
        
        self.db.execute_update(sql, params)
        result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
        return result[0]['id'] if result else 0
    
    # ==================== 系统配置 ====================
    
    def get_system_config(self, config_key: str) -> Optional[Any]:
        """根据键获取系统配置值"""
        sql = "SELECT config_value, config_type FROM system_config WHERE config_key = %s AND is_active = TRUE"
        results = self.db.execute_query(sql, (config_key,))
        
        if not results:
            return None
        
        value = results[0]['config_value']
        config_type = results[0]['config_type']
        
        # 类型转换
        if config_type == 'int':
            return int(value)
        elif config_type == 'float':
            return float(value)
        elif config_type == 'bool':
            return value.lower() in ('true', '1', 'yes')
        else:
            return value
    
    def get_system_configs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取系统配置列表"""
        sql = "SELECT * FROM system_config WHERE is_active = TRUE"
        params = None
        
        if category:
            sql += " AND category = %s"
            params = (category,)
        
        sql += " ORDER BY category, config_key"
        return self.db.execute_query(sql, params)
    
    def update_system_config(self, config_key: str, config_value: Any) -> bool:
        """更新系统配置"""
        sql = "UPDATE system_config SET config_value = %s, updated_at = NOW() WHERE config_key = %s"
        affected = self.db.execute_update(sql, (str(config_value), config_key))
        return affected > 0

