import logging
from typing import List, Optional, Literal, Dict, Any
from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

import database
from services.config_service import ConfigService
from services.agent_runtime_service import AgentRuntimeService

logger = logging.getLogger(__name__)

router = APIRouter()

def get_config_service() -> ConfigService:
    """获取配置服务实例（每次请求时动态创建）"""
    if database.db is None:
        raise HTTPException(
            status_code=500,
            detail="数据库未初始化，请确保服务已正确启动"
        )
    return ConfigService(database.db)


def get_runtime_service() -> AgentRuntimeService:
    """获取Agent运行时服务实例（每次请求时动态创建）。"""
    if database.db is None:
        raise HTTPException(
            status_code=500,
            detail="数据库未初始化，请确保服务已正确启动"
        )
    return AgentRuntimeService(database.db)


async def _load_xiaomi_did_online_map(system_user_id: int, server: str = "cn") -> Dict[str, bool]:
    from mcp_clients.mcp_device_service import get_mcp_device_service

    mcp_service = get_mcp_device_service()
    result = await mcp_service.get_user_devices(system_user_id, server)
    if result is None or not result.get("success"):
        msg = (result or {}).get("message") or "无法获取米家设备列表"
        raise HTTPException(status_code=503, detail=str(msg))
    devices = result.get("devices") or []
    out: Dict[str, bool] = {}
    for d in devices:
        if not isinstance(d, dict):
            continue
        did = str(d.get("did") or "").strip()
        if not did:
            continue
        out[did] = bool(d.get("isOnline"))
    return out


def _validate_xiaomi_bindings_online(bindings: List[Dict[str, Any]], did_to_online: Dict[str, bool]) -> None:
    for b in bindings:
        if str(b.get("source") or "").strip().lower() != "xiaomi":
            continue
        did = str(b.get("device_id") or "").strip()
        if not did:
            raise HTTPException(status_code=400, detail="米家设备 device_id 不能为空")
        if did not in did_to_online:
            raise HTTPException(status_code=400, detail=f"未找到米家设备或已不在账号下: {did}")
        if not did_to_online[did]:
            raise HTTPException(status_code=400, detail=f"米家设备离线，无法绑定: {did}")


# ==================== 数据模型 ====================

class AIModelResponse(BaseModel):
    """AI模型响应模型"""
    id: int
    model_name: str
    provider: str
    api_key: str
    api_base: str
    model_type: str = "chat"
    temperature: float = 0.7
    max_tokens: int = 2048
    is_default: bool = False
    is_active: bool = True


class AIModelUpdate(BaseModel):
    """AI模型更新模型"""
    model_name: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_type: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class AIModelCreate(BaseModel):
    """AI模型创建模型"""
    model_name: str
    provider: str
    api_key: str
    api_base: str
    model_type: str = "chat"
    temperature: float = 0.7
    max_tokens: int = 2048
    is_default: bool = False
    is_active: bool = True


class AgentResponse(BaseModel):
    """Agent响应模型"""
    id: int
    agent_code: str
    agent_name: str
    host: str = "localhost"
    port: int
    description: Optional[str] = None
    is_enabled: bool = True
    model_id: Optional[int] = None
    model_name: Optional[str] = None
    runtime_status: Optional[str] = None
    runtime_pid: Optional[int] = None
    runtime_host: Optional[str] = None
    runtime_port: Optional[int] = None
    runtime_server_ip: Optional[str] = None
    runtime_started_at: Optional[str] = None
    runtime_stopped_at: Optional[str] = None


class AgentUpdate(BaseModel):
    """Agent更新模型"""
    agent_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    runtime_command: Optional[str] = None
    runtime_cwd: Optional[str] = None


class AgentCreate(BaseModel):
    """Agent创建模型"""
    agent_code: str
    agent_name: str
    host: str = "127.0.0.1"
    port: int
    description: Optional[str] = None
    is_enabled: bool = True
    runtime_command: Optional[str] = None
    runtime_cwd: Optional[str] = None


class AgentRuntimeResponse(BaseModel):
    """Agent运行时状态响应模型"""
    agent_code: str
    agent_name: Optional[str] = None
    status: str = "stopped"
    pid: Optional[int] = None
    host: Optional[str] = None
    port: Optional[int] = None
    server_ip: Optional[str] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    command: Optional[str] = None
    cwd: Optional[str] = None
    is_running: bool = False


class AgentPromptResponse(BaseModel):
    """Agent提示词响应模型"""
    agent_code: str
    prompt_text: str


class AgentPromptUpdate(BaseModel):
    """Agent提示词更新模型"""
    prompt_text: str
    version: str = "v1.0"


class AgentModelBindingResponse(BaseModel):
    """Agent模型绑定响应模型"""
    agent_code: str
    model_id: Optional[int] = None
    model_name: Optional[str] = None


class AgentModelBindingUpdate(BaseModel):
    """Agent模型绑定更新模型"""
    model_id: Optional[int] = Field(
        default=None,
        description="绑定的模型ID；为null表示清空绑定并跟随默认模型",
    )


class AgentPluginsUpdate(BaseModel):
    """Agent 可用插件列表（仅可为系统中已开启的插件）"""
    plugin_keys: List[str] = Field(default_factory=list)


class AgentDeviceBindingItem(BaseModel):
    """Agent设备绑定项"""
    source: Literal["xiaomi", "custom"]
    device_id: str
    device_name: Optional[str] = None
    model: Optional[str] = None


class AgentDeviceBindingsResponse(BaseModel):
    """Agent设备绑定响应"""
    agent_code: str
    bindings: List[AgentDeviceBindingItem]


class AgentDeviceBindingsUpdate(BaseModel):
    """批量更新Agent设备绑定"""
    bindings: List[AgentDeviceBindingItem] = Field(default_factory=list)
    system_user_id: Optional[int] = None
    server: str = "cn"


class DeviceResponse(BaseModel):
    """设备响应模型"""
    id: int
    device_code: str
    device_name: str
    device_type: str
    agent_code: str
    ip_address: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None
    extra_config: Optional[str] = None
    is_active: bool = True


class DeviceUpdate(BaseModel):
    """设备更新模型"""
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None
    extra_config: Optional[str] = None
    is_active: Optional[bool] = None


class DeviceCreate(BaseModel):
    """设备创建模型"""
    device_code: str
    device_name: str
    device_type: str
    agent_code: str
    ip_address: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None
    extra_config: Optional[str] = None
    is_active: bool = True


class XiaomiAccountResponse(BaseModel):
    """小米账号响应模型"""
    id: int
    username: str
    password: str
    region: str = "cn"
    is_default: bool = True
    is_active: bool = True


class XiaomiAccountUpdate(BaseModel):
    """小米账号更新模型"""
    username: Optional[str] = None
    password: Optional[str] = None
    region: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class XiaomiAccountCreate(BaseModel):
    """小米账号创建模型"""
    username: str
    password: str
    region: str = "cn"
    is_default: bool = True
    is_active: bool = True


class SystemConfigResponse(BaseModel):
    """系统配置响应模型"""
    id: int
    config_key: str
    config_value: str
    config_type: str
    category: str
    description: Optional[str] = None
    is_active: bool = True


class SystemConfigUpdate(BaseModel):
    """系统配置更新模型"""
    config_value: str


class PluginModeResponse(BaseModel):
    """插件模式响应模型"""
    plugin_key: str
    mode: Literal["enabled", "disabled", "unused"]
    description: Optional[str] = None


class PluginModeUpdate(BaseModel):
    """插件模式更新模型"""
    mode: Literal["enabled", "disabled", "unused"]


class CameraPluginConfigResponse(BaseModel):
    """摄像头插件配置响应"""
    source: Literal["local", "remote"] = "local"
    local_index: int = 0
    remote_url: str = ""


class CameraPluginConfigUpdate(BaseModel):
    """摄像头插件配置更新"""
    source: Literal["local", "remote"]
    local_index: Optional[int] = 0
    remote_url: Optional[str] = ""


class AudioPluginMcpConfigResponse(BaseModel):
    """ESP32 音频 MCP（stdio）配置"""

    enabled: bool = False
    command: str = ""
    args: List[str] = Field(default_factory=list)
    cwd: str = ""
    env: Dict[str, str] = Field(default_factory=dict)


class AudioPluginMcpConfigUpdate(BaseModel):
    """ESP32 音频 MCP 配置更新"""

    enabled: bool = False
    command: str = ""
    args: List[str] = Field(default_factory=list)
    cwd: str = ""
    env: Dict[str, str] = Field(default_factory=dict)


class AudioPluginTestOutputRequest(BaseModel):
    """插件页「测试扬声器」请求（使用当前已保存的 MCP 配置）"""

    sample_rate: int = Field(default=16000, ge=4000, le=48000)
    channels: int = Field(default=1, ge=1, le=2)
    tool_name: Optional[str] = None


class AudioPluginTestOutputResponse(BaseModel):
    """插件页「测试扬声器」响应"""

    success: bool
    message: str = ""
    tool_name: Optional[str] = None
    mcp: Optional[Dict[str, Any]] = None


# ==================== AI 模型管理 ====================

@router.get("/ai-models", response_model=List[AIModelResponse])
async def get_ai_models(is_active: Optional[bool] = None):
    """获取AI模型配置列表"""
    try:
        config_service = get_config_service()
        models = config_service.get_ai_models(is_active)
        return models
    except Exception as e:
        logger.error(f"获取AI模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-models/default", response_model=AIModelResponse)
async def get_default_ai_model():
    """获取默认AI模型配置"""
    try:
        config_service = get_config_service()
        model = config_service.get_default_ai_model()
        if not model:
            raise HTTPException(status_code=404, detail="未找到默认AI模型")
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取默认AI模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-models/{model_id}", response_model=AIModelResponse)
async def get_ai_model(model_id: int):
    """根据ID获取AI模型配置"""
    try:
        config_service = get_config_service()
        model = config_service.get_ai_model_by_id(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="未找到该AI模型")
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai-models/{model_id}")
async def update_ai_model(model_id: int, data: AIModelUpdate):
    """更新AI模型配置"""
    try:
        config_service = get_config_service()
        update_data = data.model_dump(exclude_unset=True)
        success = config_service.update_ai_model(model_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该模型")
        return {"message": "更新成功", "model_id": model_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新AI模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-models", status_code=status.HTTP_201_CREATED)
async def create_ai_model(data: AIModelCreate):
    """创建新的AI模型配置"""
    try:
        config_service = get_config_service()
        model_id = config_service.create_ai_model(data.model_dump())
        return {"message": "创建成功", "model_id": model_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建AI模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent 管理 ====================

@router.get("/agents", response_model=List[AgentResponse])
async def get_agents(is_enabled: Optional[bool] = None, for_chat: bool = False):
    """获取Agent配置列表。for_chat=true 时包含主Agent（conductor）并排在首位。"""
    try:
        config_service = get_config_service()
        agents = config_service.get_agents(is_enabled, for_chat=for_chat)
        return agents
    except Exception as e:
        logger.error(f"获取Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/sync-runtimes-with-config")
async def sync_agent_runtimes_with_config():
    """
    按 agent_config.is_enabled 对齐本地进程：禁用的停止，启用的启动。
    后端启动时会自动执行一次；也可手动调用以修复漂移。
    """
    try:
        runtime_service = get_runtime_service()
        return runtime_service.sync_runtimes_with_agent_config()
    except Exception as e:
        logger.error(f"同步 Agent 进程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate):
    """创建Agent配置，并在启用时启动本地Agent进程。"""
    created_agent_code: Optional[str] = None
    try:
        config_service = get_config_service()
        runtime_service = get_runtime_service()
        payload = data.model_dump()
        runtime_command = payload.pop("runtime_command", None)
        runtime_cwd = payload.pop("runtime_cwd", None)
        agent_code = payload["agent_code"]

        agent_id = config_service.create_agent(payload)
        created_agent_code = agent_code
        if runtime_command is not None or runtime_cwd is not None:
            config_service.update_agent_runtime_launch_config(
                agent_code,
                runtime_command=runtime_command,
                runtime_cwd=runtime_cwd,
            )

        runtime_state = runtime_service.get_runtime(agent_code)
        if payload.get("is_enabled", True):
            runtime_state = runtime_service.start_agent(agent_code)

        return {
            "message": "创建成功",
            "agent_id": agent_id,
            "agent_code": agent_code,
            "runtime": runtime_state,
        }
    except ValueError as e:
        if created_agent_code:
            try:
                get_config_service().delete_agent_by_code(created_agent_code)
            except Exception:
                logger.warning("创建Agent回滚失败: %s", created_agent_code)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}", response_model=AgentResponse)
async def get_agent(agent_code: str):
    """根据代码获取Agent配置"""
    try:
        config_service = get_config_service()
        agent = config_service.get_agent_by_code(agent_code)
        if not agent:
            raise HTTPException(status_code=404, detail="未找到该Agent")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_code}")
async def delete_agent(agent_code: str):
    """删除Agent（主管家Agent不可删除）。"""
    try:
        config_service = get_config_service()
        runtime_service = get_runtime_service()

        # 尝试优雅停止（若不存在或未运行不阻断删除流程）
        try:
            runtime_service.stop_agent(agent_code)
        except ValueError:
            pass

        success = config_service.delete_agent_by_code(agent_code)
        if not success:
            raise HTTPException(status_code=404, detail="未找到该Agent")
        return {"message": "删除成功", "agent_code": agent_code}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, data: AgentUpdate):
    """更新Agent配置"""
    try:
        config_service = get_config_service()
        runtime_service = get_runtime_service()
        update_data = data.model_dump(exclude_unset=True)
        target = config_service.get_agent_by_id(agent_id)
        if not target:
            raise HTTPException(status_code=404, detail="未找到该Agent")
        agent_code = target["agent_code"]

        has_runtime_command = "runtime_command" in update_data
        has_runtime_cwd = "runtime_cwd" in update_data
        runtime_command = update_data.pop("runtime_command", None)
        runtime_cwd = update_data.pop("runtime_cwd", None)

        if update_data:
            success = config_service.update_agent(agent_id, update_data)
            if not success:
                raise HTTPException(status_code=404, detail="更新失败或未找到该Agent")

        if has_runtime_command or has_runtime_cwd:
            config_service.update_agent_runtime_launch_config(
                agent_code,
                runtime_command=runtime_command if has_runtime_command else None,
                runtime_cwd=runtime_cwd if has_runtime_cwd else None,
            )

        runtime_state = runtime_service.get_runtime(agent_code)
        if "is_enabled" in update_data:
            if bool(update_data["is_enabled"]):
                runtime_state = runtime_service.start_agent(agent_code)
            else:
                runtime_state = runtime_service.stop_agent(agent_code)

        return {
            "message": "更新成功",
            "agent_id": agent_id,
            "agent_code": agent_code,
            "runtime": runtime_state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}/runtime", response_model=AgentRuntimeResponse)
async def get_agent_runtime(agent_code: str):
    """获取Agent运行时状态。"""
    try:
        runtime_service = get_runtime_service()
        return runtime_service.get_runtime(agent_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取Agent运行状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local-ipv4")
async def get_local_ipv4():
    """本机局域网 IPv4，供前端展示服务地址（替代回环地址）。"""
    return {"ipv4": AgentRuntimeService.resolve_local_ipv4()}


@router.post("/agents/{agent_code}/runtime/start", response_model=AgentRuntimeResponse)
async def start_agent_runtime(agent_code: str):
    """启动本地Agent进程。"""
    try:
        runtime_service = get_runtime_service()
        return runtime_service.start_agent(agent_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_code}/runtime/stop", response_model=AgentRuntimeResponse)
async def stop_agent_runtime(agent_code: str):
    """停止本地Agent进程。"""
    try:
        runtime_service = get_runtime_service()
        return runtime_service.stop_agent(agent_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"停止Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}/device-bindings", response_model=AgentDeviceBindingsResponse)
async def get_agent_device_bindings(agent_code: str):
    """获取Agent绑定设备列表（米家+自定义）。"""
    try:
        config_service = get_config_service()
        bindings = config_service.get_agent_device_bindings(agent_code)
        return {"agent_code": agent_code, "bindings": bindings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取Agent设备绑定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_code}/device-bindings", response_model=AgentDeviceBindingsResponse)
async def replace_agent_device_bindings(agent_code: str, data: AgentDeviceBindingsUpdate):
    """覆盖Agent绑定设备列表。绑定米家设备时需提供 system_user_id，且仅允许在线设备。"""
    try:
        config_service = get_config_service()
        bindings_list = [item.model_dump() for item in data.bindings]
        has_xiaomi = any(str(b.get("source") or "").strip().lower() == "xiaomi" for b in bindings_list)
        if has_xiaomi and data.system_user_id is None:
            raise HTTPException(status_code=400, detail="绑定米家设备时必须提供 system_user_id")
        did_to_online: Dict[str, bool] = {}
        if data.system_user_id is not None:
            did_to_online = await _load_xiaomi_did_online_map(data.system_user_id, data.server)
        if has_xiaomi:
            _validate_xiaomi_bindings_online(bindings_list, did_to_online)
        bindings = config_service.replace_agent_device_bindings(agent_code, bindings_list)
        if data.system_user_id is not None:
            config_service.apply_agents_disable_when_all_xiaomi_offline(did_to_online)
        return {"agent_code": agent_code, "bindings": bindings}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新Agent设备绑定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_code}/device-bindings", response_model=AgentDeviceBindingsResponse)
async def bind_agent_device(agent_code: str, data: AgentDeviceBindingItem):
    """为Agent追加一个设备绑定。"""
    try:
        config_service = get_config_service()
        bindings = config_service.bind_agent_device(agent_code, data.model_dump())
        return {"agent_code": agent_code, "bindings": bindings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"绑定Agent设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_code}/device-bindings", response_model=AgentDeviceBindingsResponse)
async def unbind_agent_device(agent_code: str, source: str, device_id: str):
    """解绑Agent上的单个设备。"""
    try:
        config_service = get_config_service()
        bindings = config_service.unbind_agent_device(agent_code, source=source, device_id=device_id)
        return {"agent_code": agent_code, "bindings": bindings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"解绑Agent设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/sync-device-offline-policy")
async def sync_agent_device_offline_policy(system_user_id: int, server: str = "cn"):
    """
    根据当前米家在线状态，将「所绑米家设备全部离线」的 Agent 自动禁用（conductor 除外）。
    需在已登录且米家 MCP 可用时调用。
    """
    try:
        config_service = get_config_service()
        did_to_online = await _load_xiaomi_did_online_map(system_user_id, server)
        disabled_count = config_service.apply_agents_disable_when_all_xiaomi_offline(did_to_online)
        return {"disabled_count": disabled_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"sync_agent_device_offline_policy 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}/prompt", response_model=AgentPromptResponse)
async def get_agent_prompt(agent_code: str):
    """获取Agent的系统提示词"""
    try:
        config_service = get_config_service()
        prompt = config_service.get_agent_prompt(agent_code)
        if not prompt:
            raise HTTPException(status_code=404, detail="未找到该Agent的提示词")
        return {"agent_code": agent_code, "prompt_text": prompt}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent提示词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_code}/prompt")
async def update_agent_prompt(agent_code: str, data: AgentPromptUpdate):
    """更新Agent的系统提示词"""
    try:
        config_service = get_config_service()
        success = config_service.update_agent_prompt(
            agent_code, data.prompt_text, data.version
        )
        if not success:
            raise HTTPException(status_code=404, detail="更新失败")
        return {"message": "提示词更新成功", "agent_code": agent_code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Agent提示词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}/model-binding", response_model=AgentModelBindingResponse)
async def get_agent_model_binding(agent_code: str):
    """获取Agent绑定模型"""
    try:
        config_service = get_config_service()
        binding = config_service.get_agent_model_binding(agent_code)
        if not binding:
            raise HTTPException(status_code=404, detail="未找到该Agent")
        return binding
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent模型绑定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_code}/model-binding")
async def update_agent_model_binding(agent_code: str, data: AgentModelBindingUpdate):
    """更新Agent绑定模型"""
    try:
        config_service = get_config_service()
        success = config_service.update_agent_model_binding(agent_code, data.model_id)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该Agent")
        return {"message": "Agent模型绑定更新成功", "agent_code": agent_code}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Agent模型绑定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}/plugins")
async def get_agent_plugins_bundle(agent_code: str):
    """获取 Agent 插件配置目录（含系统插件开关与说明）。"""
    try:
        config_service = get_config_service()
        return config_service.get_agent_plugins_bundle(agent_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取 Agent 插件配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_code}/plugins")
async def replace_agent_plugins(agent_code: str, data: AgentPluginsUpdate):
    """覆盖 Agent 可用插件列表。"""
    try:
        config_service = get_config_service()
        keys = config_service.replace_agent_plugin_keys(agent_code, data.plugin_keys)
        effective = config_service.get_effective_agent_plugin_keys(agent_code)
        return {"agent_code": agent_code, "plugin_keys": keys, "effective_plugin_keys": effective}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新 Agent 插件配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 设备管理 ====================

@router.get("/devices", response_model=List[DeviceResponse])
async def get_devices(
    device_type: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """获取设备配置列表"""
    try:
        config_service = get_config_service()
        devices = config_service.get_devices(device_type, is_active)
        return devices
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_code}", response_model=DeviceResponse)
async def get_device(device_code: str):
    """根据代码获取设备配置"""
    try:
        config_service = get_config_service()
        device = config_service.get_device_by_code(device_code)
        if not device:
            raise HTTPException(status_code=404, detail="未找到该设备")
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/devices/{device_id}")
async def update_device(device_id: int, data: DeviceUpdate):
    """更新设备配置"""
    try:
        config_service = get_config_service()
        update_data = data.model_dump(exclude_unset=True)
        success = config_service.update_device(device_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该设备")
        return {"message": "更新成功", "device_id": device_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新设备配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices", status_code=status.HTTP_201_CREATED)
async def create_device(data: DeviceCreate):
    """创建新设备配置"""
    try:
        config_service = get_config_service()
        device_id = config_service.create_device(data.model_dump())
        return {"message": "创建成功", "device_id": device_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建设备配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 小米账号管理 ====================

@router.get("/xiaomi-accounts", response_model=List[XiaomiAccountResponse])
async def get_xiaomi_accounts(is_active: Optional[bool] = None):
    """获取小米账号配置列表"""
    try:
        config_service = get_config_service()
        accounts = config_service.get_xiaomi_accounts(is_active)
        return accounts
    except Exception as e:
        logger.error(f"获取小米账号配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xiaomi-accounts/default", response_model=XiaomiAccountResponse)
async def get_default_xiaomi_account():
    """获取默认小米账号"""
    try:
        config_service = get_config_service()
        account = config_service.get_default_xiaomi_account()
        if not account:
            raise HTTPException(status_code=404, detail="未找到默认小米账号")
        return account
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取默认小米账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/xiaomi-accounts/{account_id}")
async def update_xiaomi_account(account_id: int, data: XiaomiAccountUpdate):
    """更新小米账号配置"""
    try:
        config_service = get_config_service()
        update_data = data.model_dump(exclude_unset=True)
        success = config_service.update_xiaomi_account(account_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该账号")
        return {"message": "更新成功", "account_id": account_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新小米账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xiaomi-accounts", status_code=status.HTTP_201_CREATED)
async def create_xiaomi_account(data: XiaomiAccountCreate):
    """创建新小米账号"""
    try:
        config_service = get_config_service()
        account_id = config_service.create_xiaomi_account(data.model_dump())
        return {"message": "创建成功", "account_id": account_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建小米账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统配置管理 ====================

@router.get("/system-config", response_model=List[SystemConfigResponse])
async def get_system_configs(category: Optional[str] = None):
    """获取系统配置列表"""
    try:
        config_service = get_config_service()
        configs = config_service.get_system_configs(category)
        return configs
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-config/{config_key}")
async def get_system_config(config_key: str):
    """根据键获取系统配置值；未配置时返回 200 且 config_value 为 null（避免无意义的 404 日志）。"""
    try:
        config_service = get_config_service()
        value = config_service.get_system_config(config_key)
        return {"config_key": config_key, "config_value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/system-config/{config_key}")
async def update_system_config(config_key: str, data: SystemConfigUpdate):
    """更新系统配置"""
    try:
        config_service = get_config_service()
        success = config_service.update_system_config(config_key, data.config_value)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该配置项")
        return {"message": "更新成功", "config_key": config_key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 插件模式管理 ====================

@router.get("/plugins/modes", response_model=List[PluginModeResponse])
async def get_plugin_modes():
    """获取插件模式配置（enabled/disabled/unused）。"""
    try:
        config_service = get_config_service()
        return config_service.get_plugin_modes()
    except Exception as e:
        logger.error(f"获取插件模式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/{plugin_key}/mode", response_model=PluginModeResponse)
async def update_plugin_mode(plugin_key: str, data: PluginModeUpdate):
    """更新插件模式。"""
    try:
        config_service = get_config_service()
        return config_service.update_plugin_mode(plugin_key, data.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新插件模式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/camera/config", response_model=CameraPluginConfigResponse)
async def get_camera_plugin_config():
    """获取摄像头插件配置。"""
    try:
        config_service = get_config_service()
        return config_service.get_camera_plugin_config()
    except Exception as e:
        logger.error(f"获取摄像头插件配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/camera/config", response_model=CameraPluginConfigResponse)
async def update_camera_plugin_config(data: CameraPluginConfigUpdate):
    """更新摄像头插件配置。"""
    try:
        config_service = get_config_service()
        return config_service.update_camera_plugin_config(
            source=data.source,
            local_index=data.local_index,
            remote_url=data.remote_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新摄像头插件配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/audio/mcp-config", response_model=AudioPluginMcpConfigResponse)
async def get_audio_plugin_mcp_config():
    """获取 ESP32 音频 MCP（stdio）配置。"""
    try:
        config_service = get_config_service()
        return config_service.get_audio_plugin_mcp_config()
    except Exception as e:
        logger.error(f"获取音频 MCP 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/audio/mcp-config", response_model=AudioPluginMcpConfigResponse)
async def update_audio_plugin_mcp_config(data: AudioPluginMcpConfigUpdate):
    """更新 ESP32 音频 MCP（stdio）配置。"""
    try:
        config_service = get_config_service()
        return config_service.update_audio_plugin_mcp_config(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新音频 MCP 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/audio/test-output", response_model=AudioPluginTestOutputResponse)
async def test_audio_plugin_output(
    data: AudioPluginTestOutputRequest = Body(default_factory=AudioPluginTestOutputRequest),
):
    """使用已保存的 MCP 配置连接 stdio，列出工具并调用扬声器播放一段测试 PCM。"""
    try:
        config_service = get_config_service()
        cfg = config_service.get_audio_plugin_mcp_config()
        from mcp_clients.esp32_audio_mcp_service import get_esp32_audio_mcp_service

        svc = get_esp32_audio_mcp_service(yaml_config=cfg)
        raw = await svc.test_speaker_output(
            sample_rate=data.sample_rate,
            channels=data.channels,
            tool_name_override=data.tool_name,
        )
        return AudioPluginTestOutputResponse(**raw)
    except Exception as e:
        logger.exception("测试音频 MCP 输出失败")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent 注册（用户手动添加外部 Agent） ====================

class AgentRegisterRequest(BaseModel):
    """手动注册外部 Agent 的请求体"""
    url: str = Field(..., description="Agent 服务地址，如 http://localhost:12001")
    agent_code: Optional[str] = Field(
        default=None,
        description="Agent 代码标识（留空时从 AgentCard name 自动推断）",
    )
    description: Optional[str] = Field(default=None, description="功能描述（留空时从 AgentCard 取）")


class AgentRegisterResponse(BaseModel):
    """Agent 注册结果"""
    success: bool
    agent_code: str
    agent_name: str
    url: str
    host: str
    port: int
    description: Optional[str] = None
    card_fetched: bool = False
    connectivity: bool = False
    message: str = ""


@router.post("/agents/register", response_model=AgentRegisterResponse)
async def register_agent(data: AgentRegisterRequest):
    """
    手动注册一个外部 Agent 服务。

    流程：
    1. 访问 {url}/.well-known/agent-card.json 获取 AgentCard
    2. 测试 POST {url}/ 连通性
    3. 将 Agent 信息写入 agent_config 表（已存在则更新）
    4. 返回注册结果

    注册成功后 Conductor Agent 可通过 agent_code 调用该 Agent。
    """
    import httpx
    from urllib.parse import urlparse

    raw_url = data.url.rstrip("/")
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        raise HTTPException(status_code=400, detail=f"无效的 URL: {data.url}")

    host = parsed.hostname
    port = parsed.port
    if not port:
        port = 443 if parsed.scheme == "https" else 80

    # ── 1. 获取 AgentCard ────────────────────────────────────────────────────
    agent_name = ""
    description = data.description or ""
    card_fetched = False
    card_url = f"{raw_url}/.well-known/agent-card.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(card_url)
            resp.raise_for_status()
            card = resp.json()
            agent_name = card.get("name", "")
            if not description:
                description = card.get("description", "")
            card_fetched = True
            logger.info("✅ 已获取 AgentCard: name=%s url=%s", agent_name, card_url)
    except Exception as exc:
        logger.warning("⚠️  获取 AgentCard 失败 (%s): %s", card_url, exc)

    # ── 2. 推断 agent_code ───────────────────────────────────────────────────
    agent_code = (data.agent_code or "").strip()
    if not agent_code:
        # 从 agent_name 推断：去掉 "Agent" 后缀，转 snake_case，去空格
        raw = (agent_name or parsed.hostname or "unknown").lower()
        raw = raw.replace(" agent", "").replace(" ", "_").replace("-", "_")
        import re
        agent_code = re.sub(r"[^a-z0-9_]", "", raw) or "agent"
    if not agent_name:
        agent_name = agent_code.replace("_", " ").title() + " Agent"

    # ── 3. 测试连通性 ────────────────────────────────────────────────────────
    connectivity = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            probe = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "context_id": "health-check",
                        "role": "user",
                        "parts": [{"kind": "text", "text": "ping"}],
                        "message_id": "probe-001",
                    }
                },
                "id": 1,
            }
            r = await client.post(f"{raw_url}/", json=probe, headers={"Content-Type": "application/json"})
            # 2xx 或 4xx 都算服务在线（服务在线但可能拒绝了请求）
            connectivity = r.status_code < 500
    except Exception as exc:
        logger.warning("⚠️  连通性测试失败 (%s): %s", raw_url, exc)

    # ── 4. 写入 agent_config ─────────────────────────────────────────────────
    config_service = get_config_service()
    existing = config_service.get_agent_by_code(agent_code)
    message = ""
    try:
        if existing:
            config_service.update_agent(
                existing["id"],
                {
                    "agent_name": agent_name,
                    "host": host,
                    "port": port,
                    "description": description,
                    "is_enabled": True,
                },
            )
            message = f"已更新 Agent 配置: {agent_code}"
        else:
            config_service.create_agent(
                {
                    "agent_code": agent_code,
                    "agent_name": agent_name,
                    "host": host,
                    "port": port,
                    "description": description,
                    "is_enabled": True,
                }
            )
            message = f"已新增 Agent 配置: {agent_code}"
        logger.info("✅ %s (host=%s port=%s connectivity=%s)", message, host, port, connectivity)
    except Exception as exc:
        logger.error("写入 agent_config 失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"写入数据库失败: {exc}")

    return AgentRegisterResponse(
        success=True,
        agent_code=agent_code,
        agent_name=agent_name,
        url=raw_url,
        host=host,
        port=port,
        description=description or None,
        card_fetched=card_fetched,
        connectivity=connectivity,
        message=message,
    )


@router.get("/agents/registered", response_model=List[AgentRegisterResponse])
async def list_registered_agents():
    """
    列出所有已注册的外部 Agent（不含 conductor，conductor 为内嵌模式）。
    同时探测每个 Agent 的连通性。
    """
    import httpx

    config_service = get_config_service()
    rows = config_service.get_agents()
    result = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        for row in rows:
            code = row.get("agent_code", "")
            if code == "conductor":
                continue
            host = str(row.get("host") or "localhost")
            port = int(row.get("port") or 0)
            url = (
                host.rstrip("/")
                if host.startswith("http")
                else f"http://{host}:{port}"
            )

            connectivity = False
            card_fetched = False
            try:
                r = await client.get(f"{url}/.well-known/agent-card.json")
                card_fetched = r.status_code < 400
                connectivity = r.status_code < 500
            except Exception:
                pass

            result.append(
                AgentRegisterResponse(
                    success=True,
                    agent_code=code,
                    agent_name=str(row.get("agent_name") or code),
                    url=url,
                    host=host,
                    port=port,
                    description=row.get("description"),
                    card_fetched=card_fetched,
                    connectivity=connectivity,
                    message="在线" if connectivity else "离线",
                )
            )
    return result

