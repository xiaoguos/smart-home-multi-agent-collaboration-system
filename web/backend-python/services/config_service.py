import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ConfigService:
    """配置管理服务类"""
    RESERVED_AGENT_CODES = {"conductor", "data_mining"}
    PLUGIN_MODE_KEYS = {
        "xiaomi": ("plugin.xiaomi.mode", "小米插件模式（enabled/disabled/unused）"),
        "dida": ("plugin.dida.mode", "滴答插件模式（enabled/disabled/unused）"),
        "wechat": ("plugin.wechat.mode", "微信插件模式（enabled/disabled/unused）"),
        "openclaw": ("plugin.openclaw.mode", "OpenClaw插件模式（enabled/disabled/unused）"),
        "zeroclaw": ("plugin.zeroclaw.mode", "ZeroClaw插件模式（enabled/disabled/unused）"),
        "camera": ("plugin.camera.mode", "摄像头插件模式（enabled/disabled/unused）"),
        "audio": ("plugin.audio.mode", "音频插件模式（enabled/disabled/unused）"),
    }
    # 与前端插件菜单一致的标题与说明（供 Agent 配置与提示词拼装）
    PLUGIN_PUBLIC_META = {
        "xiaomi": {"title": "小米账号 / 米家", "blurb": "智能家居与设备联动，查询米家设备列表与控制"},
        "dida": {"title": "滴答清单", "blurb": "待办与任务、项目管理"},
        "wechat": {"title": "微信", "blurb": "通过微信 MCP 查询聊天记录与发送消息"},
        "openclaw": {"title": "OpenClaw", "blurb": "OpenClaw 页面嵌入与联动"},
        "zeroclaw": {"title": "ZeroClaw", "blurb": "ZeroClaw 页面嵌入与联动"},
        "camera": {"title": "摄像头", "blurb": "本地/远程摄像头输入"},
        "audio": {
            "title": "音频 / ESP32",
            "blurb": "在本页配置 stdio MCP（command/args 等）；Agent 分配后模型优先使用该 MCP",
        },
    }
    PLUGIN_ALLOWED_MODES = {"enabled", "disabled", "unused"}
    
    def __init__(self, db_connection):
        """
        初始化配置服务
        
        Args:
            db_connection: 数据库连接实例
        """
        self.db = db_connection

    # ==================== 内部通用能力 ====================

    def _is_starrocks(self) -> bool:
        return getattr(self.db, "db_type", "mysql") == "starrocks"

    def _next_id(self, table_name: str) -> int:
        row = self.db.execute_query(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table_name}")
        return int(row[0]["max_id"]) + 1 if row else 1

    def _upsert_system_config_entry(
        self,
        config_key: str,
        config_value: Any,
        config_type: str = "string",
        category: str = "system",
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> None:
        update_sql = """
            UPDATE system_config
            SET config_value = %s, config_type = %s, category = %s,
                description = %s, is_active = %s, updated_at = NOW()
            WHERE config_key = %s
        """
        affected = self.db.execute_update(
            update_sql,
            (str(config_value), config_type, category, description, bool(is_active), config_key),
        )
        if affected > 0:
            return

        if self._is_starrocks():
            insert_sql = """
                INSERT INTO system_config
                (id, config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            self.db.execute_update(
                insert_sql,
                (
                    self._next_id("system_config"),
                    config_key,
                    str(config_value),
                    config_type,
                    category,
                    description,
                    bool(is_active),
                ),
            )
            return

        insert_sql = """
            INSERT INTO system_config
            (config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        self.db.execute_update(
            insert_sql,
            (config_key, str(config_value), config_type, category, description, bool(is_active)),
        )

    def _deactivate_system_config_entry(self, config_key: str) -> None:
        self.db.execute_update(
            """
            UPDATE system_config
            SET is_active = FALSE, updated_at = NOW()
            WHERE config_key = %s
            """,
            (config_key,),
        )

    @staticmethod
    def _infer_config_type_and_value(config_value: Any) -> tuple[str, str]:
        if isinstance(config_value, bool):
            return "bool", "true" if config_value else "false"
        if isinstance(config_value, int):
            return "int", str(config_value)
        if isinstance(config_value, float):
            return "float", str(config_value)
        if isinstance(config_value, (dict, list)):
            return "json", json.dumps(config_value, ensure_ascii=False)
        return "string", str(config_value)

    @staticmethod
    def _infer_config_category(config_key: str) -> str:
        if config_key.startswith("plugin."):
            return "plugin"
        if config_key.startswith("agent_") or config_key.startswith("agent."):
            return "agent"
        return "system"

    def _get_agent_runtime_map(self) -> Dict[str, Dict[str, Any]]:
        sql = """
            SELECT config_key, config_value
            FROM system_config
            WHERE config_key LIKE 'agent_runtime.%' AND is_active = TRUE
        """
        rows = self.db.execute_query(sql)
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            config_key = str(row.get("config_key") or "")
            parts = config_key.split(".")
            if len(parts) < 3:
                continue
            _, agent_code, field = parts[0], parts[1], ".".join(parts[2:])
            result.setdefault(agent_code, {})[field] = row.get("config_value")
        return result

    def _attach_runtime_fields(
        self,
        agent: Dict[str, Any],
        runtime_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        runtime_data = (runtime_map or {}).get(str(agent.get("agent_code") or ""), {})

        def _to_int(v: Any) -> Optional[int]:
            if v is None:
                return None
            try:
                return int(str(v))
            except (TypeError, ValueError):
                return None

        agent["runtime_status"] = runtime_data.get("status") or "stopped"
        agent["runtime_pid"] = _to_int(runtime_data.get("pid"))
        agent["runtime_host"] = runtime_data.get("host")
        agent["runtime_port"] = _to_int(runtime_data.get("port"))
        agent["runtime_server_ip"] = runtime_data.get("server_ip")
        agent["runtime_started_at"] = runtime_data.get("started_at")
        agent["runtime_stopped_at"] = runtime_data.get("stopped_at")
        return agent
    
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
        sql = """
            SELECT * FROM ai_model_config
            WHERE is_default = TRUE AND is_active = TRUE
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
        """
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

        # 保证默认模型唯一，且默认模型必须启用
        if data.get("is_default") is True:
            target = self.db.execute_query(
                "SELECT id FROM ai_model_config WHERE id = %s LIMIT 1",
                (model_id,),
            )
            if not target:
                return False
            if data.get("is_active") is False:
                raise ValueError("默认模型必须处于启用状态")
            self.db.execute_update(
                "UPDATE ai_model_config SET is_default = FALSE, updated_at = NOW() WHERE id <> %s",
                (model_id,),
            )
        
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

        # 默认模型必须启用；创建新默认时先取消其他默认
        if data.get("is_default", False) and not data.get("is_active", True):
            raise ValueError("默认模型必须处于启用状态")
        if data.get("is_default", False):
            self.db.execute_update(
                "UPDATE ai_model_config SET is_default = FALSE, updated_at = NOW() WHERE is_default = TRUE"
            )
        
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

    def _get_active_agent_model_bindings(self) -> Dict[str, int]:
        """获取启用的 Agent -> 模型ID 绑定关系。"""
        sql = """
            SELECT config_key, config_value
            FROM system_config
            WHERE config_key LIKE 'agent_model.%' AND is_active = TRUE
        """
        rows = self.db.execute_query(sql)
        bindings: Dict[str, int] = {}
        for row in rows:
            config_key = str(row.get("config_key") or "")
            if not config_key.startswith("agent_model."):
                continue
            agent_code = config_key.removeprefix("agent_model.").strip()
            raw_value = str(row.get("config_value") or "").strip()
            if not agent_code or not raw_value:
                continue
            try:
                bindings[agent_code] = int(raw_value)
            except (TypeError, ValueError):
                logger.warning(f"忽略非法Agent模型绑定值: {config_key}={raw_value}")
        return bindings

    def _get_ai_model_name_map(self, model_ids: List[int]) -> Dict[int, str]:
        """批量查询模型ID到模型名称的映射。"""
        if not model_ids:
            return {}
        unique_ids = sorted(set(model_ids))
        placeholders = ", ".join(["%s"] * len(unique_ids))
        sql = f"SELECT id, model_name FROM ai_model_config WHERE id IN ({placeholders}) AND is_active = TRUE"
        rows = self.db.execute_query(sql, tuple(unique_ids))
        return {int(row["id"]): str(row["model_name"]) for row in rows}
    
    def get_agents(self, is_enabled: Optional[bool] = None, for_chat: bool = False) -> List[Dict[str, Any]]:
        """
        获取Agent配置列表

        Args:
            is_enabled: 是否只获取启用的Agent
            for_chat: 为 True 时包含主 Agent（conductor），且 conductor 排在列表最前面

        Returns:
            Agent配置列表
        """
        if for_chat:
            sql = "SELECT * FROM agent_config WHERE 1=1"
        else:
            sql = "SELECT * FROM agent_config WHERE agent_code != 'conductor'"
        params = None

        if is_enabled is not None:
            sql += " AND is_enabled = %s"
            params = (is_enabled,)

        sql += " ORDER BY CASE WHEN agent_code = 'conductor' THEN 0 ELSE 1 END, id ASC"
        agents = self.db.execute_query(sql, params)

        # 附加每个Agent当前绑定模型信息（无绑定则为None，表示跟随默认模型）
        bindings = self._get_active_agent_model_bindings()
        model_name_map = self._get_ai_model_name_map(list(bindings.values()))
        runtime_map = self._get_agent_runtime_map()
        for agent in agents:
            agent_code = str(agent.get("agent_code") or "")
            bound_model_id = bindings.get(agent_code)
            bound_model_name = model_name_map.get(bound_model_id) if bound_model_id is not None else None
            agent["model_id"] = bound_model_id if bound_model_name else None
            agent["model_name"] = bound_model_name
            self._attach_runtime_fields(agent, runtime_map)

        return agents
    
    def get_agent_by_code(self, agent_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取Agent配置"""
        sql = "SELECT * FROM agent_config WHERE agent_code = %s"
        results = self.db.execute_query(sql, (agent_code,))
        if not results:
            return None

        agent = results[0]
        bindings = self._get_active_agent_model_bindings()
        bound_model_id = bindings.get(agent_code)
        bound_model_name = None
        if bound_model_id is not None:
            name_map = self._get_ai_model_name_map([bound_model_id])
            bound_model_name = name_map.get(bound_model_id)
        agent["model_id"] = bound_model_id if bound_model_name else None
        agent["model_name"] = bound_model_name
        self._attach_runtime_fields(agent, self._get_agent_runtime_map())
        return agent

    def get_agent_by_id(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取Agent配置。"""
        sql = "SELECT * FROM agent_config WHERE id = %s LIMIT 1"
        rows = self.db.execute_query(sql, (agent_id,))
        if not rows:
            return None
        return self.get_agent_by_code(str(rows[0].get("agent_code") or ""))
    
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

    def create_agent(self, data: Dict[str, Any]) -> int:
        """创建Agent配置。"""
        required_fields = ["agent_code", "agent_name", "host", "port"]
        for field in required_fields:
            if field not in data or data[field] in (None, ""):
                raise ValueError(f"缺少必填字段: {field}")

        agent_code = str(data["agent_code"]).strip()
        if not agent_code:
            raise ValueError("agent_code 不能为空")

        exists = self.get_agent_by_code(agent_code)
        if exists:
            raise ValueError(f"Agent已存在: {agent_code}")

        sql = """
            INSERT INTO agent_config
            (agent_code, agent_name, host, port, description, is_enabled, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        params = (
            agent_code,
            str(data["agent_name"]).strip(),
            str(data.get("host") or "127.0.0.1").strip(),
            int(data["port"]),
            data.get("description"),
            bool(data.get("is_enabled", True)),
        )
        self.db.execute_update(sql, params)
        row = self.db.execute_query(
            "SELECT id FROM agent_config WHERE agent_code = %s LIMIT 1",
            (agent_code,),
        )
        if not row:
            raise ValueError("Agent创建后读取失败")
        return int(row[0]["id"])

    def delete_agent_by_code(self, agent_code: str) -> bool:
        """删除Agent（禁止删除保留Agent）。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if normalized in self.RESERVED_AGENT_CODES:
            raise ValueError("主管家Agent禁止删除")

        agent = self.get_agent_by_code(normalized)
        if not agent:
            return False

        # 避免删除后遗留自定义设备孤儿绑定
        device_refs = self.db.execute_query(
            "SELECT COUNT(*) AS cnt FROM device_config WHERE agent_code = %s",
            (normalized,),
        )
        if device_refs and int(device_refs[0].get("cnt") or 0) > 0:
            raise ValueError("该Agent仍绑定了自定义设备，请先解绑后再删除")

        self.db.execute_update("DELETE FROM agent_config WHERE agent_code = %s", (normalized,))
        self.db.execute_update("DELETE FROM agent_prompt WHERE agent_code = %s", (normalized,))
        self.db.execute_update(
            "DELETE FROM system_config WHERE config_key = %s OR config_key LIKE %s OR config_key = %s",
            (
                f"agent_model.{normalized}",
                f"agent_runtime.{normalized}.%",
                f"agent_device_bindings.{normalized}",
            ),
        )
        return True

    def get_agent_runtime_launch_config(self, agent_code: str) -> Dict[str, Optional[str]]:
        """获取Agent本地启动命令配置。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")

        sql = """
            SELECT config_key, config_value
            FROM system_config
            WHERE config_key IN (%s, %s) AND is_active = TRUE
        """
        command_key = f"agent_runtime.{normalized}.command"
        cwd_key = f"agent_runtime.{normalized}.cwd"
        rows = self.db.execute_query(sql, (command_key, cwd_key))
        result = {"runtime_command": None, "runtime_cwd": None}
        for row in rows:
            key = str(row.get("config_key") or "")
            value = row.get("config_value")
            if key == command_key:
                result["runtime_command"] = str(value or "").strip() or None
            if key == cwd_key:
                result["runtime_cwd"] = str(value or "").strip() or None
        return result

    def update_agent_runtime_launch_config(
        self,
        agent_code: str,
        runtime_command: Optional[str] = None,
        runtime_cwd: Optional[str] = None,
    ) -> None:
        """更新Agent本地启动配置。传空字符串会清除对应配置。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if not self.get_agent_by_code(normalized):
            raise ValueError(f"未找到Agent: {normalized}")

        command_key = f"agent_runtime.{normalized}.command"
        cwd_key = f"agent_runtime.{normalized}.cwd"

        if runtime_command is not None:
            cmd = str(runtime_command).strip()
            if cmd:
                self._upsert_system_config_entry(
                    command_key,
                    cmd,
                    config_type="string",
                    category="agent",
                    description=f"{normalized} 本地启动命令",
                    is_active=True,
                )
            else:
                self._deactivate_system_config_entry(command_key)

        if runtime_cwd is not None:
            cwd = str(runtime_cwd).strip()
            if cwd:
                self._upsert_system_config_entry(
                    cwd_key,
                    cwd,
                    config_type="string",
                    category="agent",
                    description=f"{normalized} 本地启动工作目录",
                    is_active=True,
                )
            else:
                self._deactivate_system_config_entry(cwd_key)

    def get_agent_runtime_state(self, agent_code: str) -> Dict[str, Any]:
        """读取Agent运行时状态（来自 system_config）。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if not self.get_agent_by_code(normalized):
            raise ValueError(f"未找到Agent: {normalized}")

        runtime_map = self._get_agent_runtime_map()
        runtime = runtime_map.get(normalized, {})

        def _to_int(value: Any) -> Optional[int]:
            try:
                return int(str(value)) if value not in (None, "") else None
            except (TypeError, ValueError):
                return None

        return {
            "agent_code": normalized,
            "status": runtime.get("status") or "stopped",
            "pid": _to_int(runtime.get("pid")),
            "host": runtime.get("host"),
            "port": _to_int(runtime.get("port")),
            "server_ip": runtime.get("server_ip"),
            "started_at": runtime.get("started_at"),
            "stopped_at": runtime.get("stopped_at"),
            "command": runtime.get("command"),
            "cwd": runtime.get("cwd"),
        }

    @staticmethod
    def _agent_device_bindings_key(agent_code: str) -> str:
        return f"agent_device_bindings.{agent_code}"

    @staticmethod
    def _normalize_agent_device_binding(item: Dict[str, Any]) -> Dict[str, Any]:
        source = str(item.get("source") or "").strip().lower()
        if source not in {"xiaomi", "custom"}:
            raise ValueError("设备来源仅支持 xiaomi 或 custom")

        device_id = str(item.get("device_id") or "").strip()
        if not device_id:
            raise ValueError("device_id 不能为空")

        normalized = {
            "source": source,
            "device_id": device_id,
            "device_name": str(item.get("device_name") or "").strip() or None,
            "model": str(item.get("model") or "").strip() or None,
        }
        return normalized

    def get_agent_device_bindings(self, agent_code: str) -> List[Dict[str, Any]]:
        """获取Agent绑定设备列表。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if not self.get_agent_by_code(normalized):
            raise ValueError(f"未找到Agent: {normalized}")

        key = self._agent_device_bindings_key(normalized)
        rows = self.db.execute_query(
            """
            SELECT config_value
            FROM system_config
            WHERE config_key = %s AND is_active = TRUE
            LIMIT 1
            """,
            (key,),
        )
        if not rows:
            return []

        raw = str(rows[0].get("config_value") or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("设备绑定配置损坏，已忽略: %s", key)
            return []

        if not isinstance(parsed, list):
            return []

        normalized_list: List[Dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            try:
                normalized_list.append(self._normalize_agent_device_binding(item))
            except ValueError:
                continue
        return normalized_list

    def replace_agent_device_bindings(self, agent_code: str, bindings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """覆盖Agent绑定设备列表。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if not self.get_agent_by_code(normalized):
            raise ValueError(f"未找到Agent: {normalized}")

        normalized_list: List[Dict[str, Any]] = []
        seen = set()
        for item in bindings:
            normalized_item = self._normalize_agent_device_binding(item)
            unique_key = f"{normalized_item['source']}:{normalized_item['device_id']}"
            if unique_key in seen:
                continue
            seen.add(unique_key)
            if normalized_item["source"] == "custom":
                exists = self.db.execute_query(
                    "SELECT id FROM device_config WHERE device_code = %s AND is_active = TRUE LIMIT 1",
                    (normalized_item["device_id"],),
                )
                if not exists:
                    raise ValueError(f"未找到启用中的自定义设备: {normalized_item['device_id']}")
            normalized_list.append(normalized_item)

        key = self._agent_device_bindings_key(normalized)
        if not normalized_list:
            self._deactivate_system_config_entry(key)
            return []

        self._upsert_system_config_entry(
            key,
            json.dumps(normalized_list, ensure_ascii=False),
            config_type="json",
            category="agent",
            description=f"{normalized} 绑定设备清单（米家+自定义）",
            is_active=True,
        )
        return normalized_list

    def bind_agent_device(self, agent_code: str, binding: Dict[str, Any]) -> List[Dict[str, Any]]:
        """向Agent追加一个设备绑定。"""
        current = self.get_agent_device_bindings(agent_code)
        normalized = self._normalize_agent_device_binding(binding)
        if normalized["source"] == "custom":
            exists = self.db.execute_query(
                "SELECT id FROM device_config WHERE device_code = %s AND is_active = TRUE LIMIT 1",
                (normalized["device_id"],),
            )
            if not exists:
                raise ValueError(f"未找到启用中的自定义设备: {normalized['device_id']}")

        replaced = False
        for idx, item in enumerate(current):
            if item["source"] == normalized["source"] and item["device_id"] == normalized["device_id"]:
                current[idx] = normalized
                replaced = True
                break
        if not replaced:
            current.append(normalized)
        return self.replace_agent_device_bindings(agent_code, current)

    def unbind_agent_device(self, agent_code: str, source: str, device_id: str) -> List[Dict[str, Any]]:
        """解绑Agent上的一个设备。"""
        normalized_source = str(source or "").strip().lower()
        normalized_device_id = str(device_id or "").strip()
        if normalized_source not in {"xiaomi", "custom"}:
            raise ValueError("source 必须是 xiaomi 或 custom")
        if not normalized_device_id:
            raise ValueError("device_id 不能为空")

        current = self.get_agent_device_bindings(agent_code)
        remain = [
            item
            for item in current
            if not (item["source"] == normalized_source and item["device_id"] == normalized_device_id)
        ]
        return self.replace_agent_device_bindings(agent_code, remain)

    def apply_agents_disable_when_all_xiaomi_offline(self, did_to_online: Dict[str, bool]) -> int:
        """
        若某 Agent 仅考虑其绑定的米家设备：全部离线时自动禁用该 Agent。
        conductor 不自动禁用。仅含自定义设备绑定的 Agent 不受影响。
        """
        disabled = 0
        agents = self.get_agents()
        for agent in agents:
            code = str(agent.get("agent_code") or "").strip()
            if code in self.RESERVED_AGENT_CODES:
                continue
            try:
                bindings = self.get_agent_device_bindings(code)
            except ValueError:
                continue
            xiaomi_dids = [
                str(b.get("device_id") or "").strip()
                for b in bindings
                if str(b.get("source") or "").strip().lower() == "xiaomi" and str(b.get("device_id") or "").strip()
            ]
            if not xiaomi_dids:
                continue
            any_online = any(did_to_online.get(did, False) for did in xiaomi_dids)
            if any_online:
                continue
            agent_id = agent.get("id")
            if agent_id is None:
                continue
            if agent.get("is_enabled") and self.update_agent(int(agent_id), {"is_enabled": False}):
                disabled += 1
        return disabled

    def get_agent_model_binding(self, agent_code: str) -> Optional[Dict[str, Any]]:
        """获取指定Agent的模型绑定（无绑定表示跟随默认模型）。"""
        agent = self.get_agent_by_code(agent_code)
        if not agent:
            return None
        return {
            "agent_code": agent_code,
            "model_id": agent.get("model_id"),
            "model_name": agent.get("model_name"),
        }

    def update_agent_model_binding(self, agent_code: str, model_id: Optional[int]) -> bool:
        """更新指定Agent的模型绑定。model_id=None 表示清空绑定并跟随默认模型。"""
        agent = self.get_agent_by_code(agent_code)
        if not agent:
            return False

        config_key = f"agent_model.{agent_code}"
        description = f"Agent {agent_code} 绑定模型ID（为空表示跟随默认模型）"

        if model_id is None:
            # 清空绑定：标记为不活跃
            sql = """
                UPDATE system_config
                SET config_value = '', is_active = FALSE, updated_at = NOW()
                WHERE config_key = %s
            """
            self.db.execute_update(sql, (config_key,))
            return True

        model = self.db.execute_query(
            "SELECT id, model_name, is_active FROM ai_model_config WHERE id = %s LIMIT 1",
            (model_id,),
        )
        if not model:
            raise ValueError(f"未找到模型ID: {model_id}")
        if not bool(model[0].get("is_active")):
            raise ValueError(f"模型未启用，无法绑定: {model[0].get('model_name')}")

        update_sql = """
            UPDATE system_config
            SET config_value = %s, config_type = 'int', category = 'agent',
                description = %s, is_active = TRUE, updated_at = NOW()
            WHERE config_key = %s
        """
        affected = self.db.execute_update(update_sql, (str(model_id), description, config_key))
        if affected > 0:
            return True

        db_type = getattr(self.db, "db_type", "mysql")
        if db_type == "starrocks":
            max_id_row = self.db.execute_query("SELECT COALESCE(MAX(id), 0) AS max_id FROM system_config")
            next_id = int(max_id_row[0]["max_id"]) + 1 if max_id_row else 1
            insert_sql = """
                INSERT INTO system_config
                (id, config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, 'int', 'agent', %s, TRUE, NOW(), NOW())
            """
            self.db.execute_update(insert_sql, (next_id, config_key, str(model_id), description))
        else:
            insert_sql = """
                INSERT INTO system_config
                (config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
                VALUES (%s, %s, 'int', 'agent', %s, TRUE, NOW(), NOW())
            """
            self.db.execute_update(insert_sql, (config_key, str(model_id), description))

        return True
    
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
        # 直接更新激活的提示词
        sql_update = """
            UPDATE agent_prompt 
            SET prompt_text = %s, version = %s, updated_at = NOW()
            WHERE agent_code = %s AND is_active = TRUE
        """
        affected = self.db.execute_update(sql_update, (prompt_text, version, agent_code))
        
        # 如果没有激活的记录，查询最大 id 并插入新记录
        if affected == 0:
            # 获取最大 id
            sql_max_id = "SELECT COALESCE(MAX(id), 0) as max_id FROM agent_prompt"
            result = self.db.execute_query(sql_max_id)
            next_id = result[0]['max_id'] + 1 if result else 1
            
            # 插入新记录
            sql_insert = """
                INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW())
            """
            affected = self.db.execute_update(sql_insert, (next_id, agent_code, prompt_text, version))
        
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
            return str(value).lower() in ('true', '1', 'yes')
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
        """更新系统配置（不存在时自动创建）。"""
        config_type, normalized_value = self._infer_config_type_and_value(config_value)
        category = self._infer_config_category(config_key)
        self._upsert_system_config_entry(
            config_key=config_key,
            config_value=normalized_value,
            config_type=config_type,
            category=category,
            description=f"系统配置: {config_key}",
            is_active=True,
        )
        return True

    def _get_plugin_mode_map(self) -> Dict[str, str]:
        """各插件当前 mode（enabled/disabled/unused）。"""
        result: Dict[str, str] = {}
        for plugin_key, (config_key, _desc) in self.PLUGIN_MODE_KEYS.items():
            raw_value = self.get_system_config(config_key)
            mode = str(raw_value).strip().lower() if raw_value is not None else "unused"
            if mode not in self.PLUGIN_ALLOWED_MODES:
                mode = "unused"
            result[plugin_key] = mode
        return result

    def _agent_plugins_config_key(self, agent_code: str) -> str:
        return f"agent_plugins.{(agent_code or '').strip()}"

    def get_raw_agent_plugin_keys(self, agent_code: str) -> Optional[List[str]]:
        """
        读取 Agent 配置的插件列表。
        None 表示尚未保存过配置（沿用「当前所有已开启插件」默认）；
        空列表表示显式不启用任何插件能力。
        """
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if not self.get_agent_by_code(normalized):
            raise ValueError(f"未找到Agent: {normalized}")

        key = self._agent_plugins_config_key(normalized)
        rows = self.db.execute_query(
            """
            SELECT config_value
            FROM system_config
            WHERE config_key = %s AND is_active = TRUE
            LIMIT 1
            """,
            (key,),
        )
        if not rows:
            return None
        raw = rows[0].get("config_value")
        if raw is None or str(raw).strip() == "":
            return []
        try:
            parsed = json.loads(str(raw))
        except json.JSONDecodeError:
            logger.warning("agent_plugins JSON 损坏: %s", key)
            return []
        if not isinstance(parsed, list):
            return []
        return [str(x).strip().lower() for x in parsed if str(x).strip()]

    def get_effective_agent_plugin_keys(self, agent_code: str) -> List[str]:
        """全局已开启且 Agent 已勾选的插件（用于运行时与工具集）。"""
        modes = self._get_plugin_mode_map()
        raw = self.get_raw_agent_plugin_keys(agent_code)
        if raw is None:
            return [k for k, m in modes.items() if m == "enabled"]
        return [k for k in raw if modes.get(k) == "enabled"]

    def replace_agent_plugin_keys(self, agent_code: str, keys: List[str]) -> List[str]:
        """覆盖 Agent 可用插件；仅允许当前全局为 enabled 的插件。"""
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")
        if not self.get_agent_by_code(normalized):
            raise ValueError(f"未找到Agent: {normalized}")

        modes = self._get_plugin_mode_map()
        seen = set()
        clean: List[str] = []
        for k in keys:
            kk = str(k).strip().lower()
            if not kk or kk in seen:
                continue
            if kk not in self.PLUGIN_MODE_KEYS:
                raise ValueError(f"不支持的插件: {kk}")
            if modes.get(kk) != "enabled":
                raise ValueError(f"插件未在系统中开启，无法分配给 Agent: {kk}")
            seen.add(kk)
            clean.append(kk)

        cfg_key = self._agent_plugins_config_key(normalized)
        self._upsert_system_config_entry(
            config_key=cfg_key,
            config_value=json.dumps(clean, ensure_ascii=False),
            config_type="json",
            category="agent",
            description=f"{normalized} 可用插件列表（仅 enabled 插件可写入）",
            is_active=True,
        )
        return clean

    def get_agent_plugins_bundle(self, agent_code: str) -> Dict[str, Any]:
        """供前端展示：目录 + 选中态 + 生效列表。"""
        modes = self._get_plugin_mode_map()
        raw = self.get_raw_agent_plugin_keys(agent_code)
        effective = self.get_effective_agent_plugin_keys(agent_code)

        catalog: List[Dict[str, Any]] = []
        for plugin_key, (_ck, sys_desc) in self.PLUGIN_MODE_KEYS.items():
            meta = self.PLUGIN_PUBLIC_META.get(plugin_key) or {}
            title = str(meta.get("title") or plugin_key)
            blurb = str(meta.get("blurb") or sys_desc)
            mode = modes.get(plugin_key, "unused")
            enabled_globally = mode == "enabled"
            if raw is None:
                selected = enabled_globally
            else:
                selected = plugin_key in raw
            catalog.append(
                {
                    "plugin_key": plugin_key,
                    "mode": mode,
                    "title": title,
                    "description": blurb,
                    "selected": selected and enabled_globally,
                    "allow_assign": enabled_globally,
                }
            )

        return {
            "agent_code": agent_code.strip(),
            "plugin_keys": raw,
            "effective_plugin_keys": effective,
            "catalog": catalog,
        }

    def get_plugin_modes(self) -> List[Dict[str, Any]]:
        """获取插件模式配置。"""
        result: List[Dict[str, Any]] = []
        for plugin_key, (config_key, description) in self.PLUGIN_MODE_KEYS.items():
            raw_value = self.get_system_config(config_key)
            mode = str(raw_value).strip().lower() if raw_value is not None else "unused"
            if mode not in self.PLUGIN_ALLOWED_MODES:
                mode = "unused"
            result.append(
                {
                    "plugin_key": plugin_key,
                    "mode": mode,
                    "description": description,
                }
            )
        return result

    def update_plugin_mode(self, plugin_key: str, mode: str) -> Dict[str, Any]:
        """更新指定插件模式。"""
        normalized_plugin_key = str(plugin_key or "").strip().lower()
        normalized_mode = str(mode or "").strip().lower()
        if normalized_plugin_key not in self.PLUGIN_MODE_KEYS:
            raise ValueError(f"不支持的插件: {plugin_key}")
        if normalized_mode not in self.PLUGIN_ALLOWED_MODES:
            raise ValueError("mode 必须是 enabled / disabled / unused")

        config_key, description = self.PLUGIN_MODE_KEYS[normalized_plugin_key]
        self._upsert_system_config_entry(
            config_key=config_key,
            config_value=normalized_mode,
            config_type="string",
            category="plugin",
            description=description,
            is_active=True,
        )
        return {
            "plugin_key": normalized_plugin_key,
            "mode": normalized_mode,
            "description": description,
        }

    def get_camera_plugin_config(self) -> Dict[str, Any]:
        """获取摄像头插件配置（本地/远程）。"""
        source_raw = self.get_system_config("plugin.camera.source")
        local_index_raw = self.get_system_config("plugin.camera.local_index")
        remote_url_raw = self.get_system_config("plugin.camera.remote_url")

        source = str(source_raw).strip().lower() if source_raw is not None else "local"
        if source not in {"local", "remote"}:
            source = "local"

        local_index = 0
        if local_index_raw is not None:
            try:
                local_index = int(local_index_raw)
            except (TypeError, ValueError):
                local_index = 0

        remote_url = str(remote_url_raw).strip() if remote_url_raw is not None else ""
        return {
            "source": source,
            "local_index": local_index,
            "remote_url": remote_url,
        }

    def update_camera_plugin_config(
        self,
        source: str,
        local_index: Optional[int] = None,
        remote_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新摄像头插件配置。"""
        normalized_source = str(source or "").strip().lower()
        if normalized_source not in {"local", "remote"}:
            raise ValueError("source 必须是 local 或 remote")

        normalized_local_index = 0 if local_index is None else int(local_index)
        if normalized_local_index < 0:
            raise ValueError("local_index 不能小于 0")

        normalized_remote_url = str(remote_url or "").strip()
        if normalized_source == "remote" and not normalized_remote_url:
            raise ValueError("远程摄像头模式需要填写 remote_url")

        self._upsert_system_config_entry(
            config_key="plugin.camera.source",
            config_value=normalized_source,
            config_type="string",
            category="plugin",
            description="摄像头插件来源（local/remote）",
            is_active=True,
        )
        self._upsert_system_config_entry(
            config_key="plugin.camera.local_index",
            config_value=str(normalized_local_index),
            config_type="int",
            category="plugin",
            description="本地摄像头设备索引",
            is_active=True,
        )
        self._upsert_system_config_entry(
            config_key="plugin.camera.remote_url",
            config_value=normalized_remote_url,
            config_type="string",
            category="plugin",
            description="远程摄像头URL",
            is_active=True,
        )
        return self.get_camera_plugin_config()

    @staticmethod
    def _normalize_audio_mcp_config_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        enabled = bool(data.get("enabled", False))
        command = str(data.get("command") or "").strip()
        cwd = str(data.get("cwd") or "").strip()
        raw_args = data.get("args")
        args: List[str] = []
        if isinstance(raw_args, list):
            args = [str(x) for x in raw_args]
        elif isinstance(raw_args, str) and raw_args.strip():
            try:
                parsed = json.loads(raw_args.strip())
                if isinstance(parsed, list):
                    args = [str(x) for x in parsed]
                else:
                    args = raw_args.split()
            except json.JSONDecodeError:
                args = raw_args.split()
        env: Dict[str, str] = {}
        raw_env = data.get("env")
        if isinstance(raw_env, dict):
            env = {str(k): str(v) for k, v in raw_env.items()}
        return {
            "enabled": enabled,
            "command": command,
            "args": args,
            "cwd": cwd,
            "env": env,
        }

    def _load_esp32_audio_mcp_from_yaml_files(self) -> Dict[str, Any]:
        """无数据库记录时，与 Agent 侧一致从仓库根 config.yaml 读取 esp32_audio_mcp / esp32_arduino。"""
        try:
            import yaml
        except ImportError:
            return {}
        root = Path(__file__).resolve().parents[3]
        for candidate in (root / "config.yaml", root.parent / "config.yaml"):
            if not candidate.exists():
                continue
            try:
                with open(candidate, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                raw = data.get("esp32_audio_mcp")
                if not isinstance(raw, dict) or not raw:
                    raw = data.get("esp32_arduino")
                if isinstance(raw, dict) and raw:
                    return dict(raw)
            except Exception as e:
                logger.warning("读取 config.yaml esp32 音频段失败: %s", e)
        return {}

    def get_audio_plugin_mcp_config(self) -> Dict[str, Any]:
        """获取 ESP32 音频 MCP（stdio）配置：优先数据库 plugin.audio.mcp_config，否则回退 config.yaml。"""
        yaml_fallback = self._load_esp32_audio_mcp_from_yaml_files()
        rows = self.db.execute_query(
            """
            SELECT config_value, config_type
            FROM system_config
            WHERE config_key = %s AND is_active = TRUE
            LIMIT 1
            """,
            ("plugin.audio.mcp_config",),
        )
        if not rows:
            return self._normalize_audio_mcp_config_payload(yaml_fallback)
        raw_val = rows[0].get("config_value")
        if raw_val is None or str(raw_val).strip() == "":
            return self._normalize_audio_mcp_config_payload(yaml_fallback)
        try:
            parsed = json.loads(str(raw_val))
        except json.JSONDecodeError:
            logger.warning("plugin.audio.mcp_config 损坏，已回退 config.yaml")
            return self._normalize_audio_mcp_config_payload(yaml_fallback)
        if not isinstance(parsed, dict):
            return self._normalize_audio_mcp_config_payload(yaml_fallback)
        return self._normalize_audio_mcp_config_payload(parsed)

    def update_audio_plugin_mcp_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新 ESP32 音频 MCP 配置（写入数据库；之后 Conductor 优先读库）。"""
        normalized = self._normalize_audio_mcp_config_payload(data)
        if normalized["enabled"] and not normalized["command"]:
            raise ValueError("启用 MCP 时必须填写 command（可执行文件或解释器路径）")
        self._upsert_system_config_entry(
            config_key="plugin.audio.mcp_config",
            config_value=json.dumps(normalized, ensure_ascii=False),
            config_type="json",
            category="plugin",
            description="ESP32 音频 MCP（stdio）连接参数",
            is_active=True,
        )
        return self.get_audio_plugin_mcp_config()

