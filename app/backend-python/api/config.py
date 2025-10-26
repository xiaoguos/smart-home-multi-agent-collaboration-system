"""
配置管理 API
提供系统配置、AI模型、Agent、设备等配置的管理接口
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from database import db
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter()
config_service = ConfigService(db)


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


class AgentUpdate(BaseModel):
    """Agent更新模型"""
    agent_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class AgentPromptResponse(BaseModel):
    """Agent提示词响应模型"""
    agent_code: str
    prompt_text: str


class AgentPromptUpdate(BaseModel):
    """Agent提示词更新模型"""
    prompt_text: str
    version: str = "v1.0"


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


# ==================== AI 模型管理 ====================

@router.get("/ai-models", response_model=List[AIModelResponse])
async def get_ai_models(is_active: Optional[bool] = None):
    """获取AI模型配置列表"""
    try:
        models = config_service.get_ai_models(is_active)
        return models
    except Exception as e:
        logger.error(f"获取AI模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-models/default", response_model=AIModelResponse)
async def get_default_ai_model():
    """获取默认AI模型配置"""
    try:
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
        update_data = data.model_dump(exclude_unset=True)
        success = config_service.update_ai_model(model_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该模型")
        return {"message": "更新成功", "model_id": model_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新AI模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-models", status_code=status.HTTP_201_CREATED)
async def create_ai_model(data: AIModelCreate):
    """创建新的AI模型配置"""
    try:
        model_id = config_service.create_ai_model(data.model_dump())
        return {"message": "创建成功", "model_id": model_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建AI模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent 管理 ====================

@router.get("/agents", response_model=List[AgentResponse])
async def get_agents(is_enabled: Optional[bool] = None):
    """获取Agent配置列表"""
    try:
        agents = config_service.get_agents(is_enabled)
        return agents
    except Exception as e:
        logger.error(f"获取Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}", response_model=AgentResponse)
async def get_agent(agent_code: str):
    """根据代码获取Agent配置"""
    try:
        agent = config_service.get_agent_by_code(agent_code)
        if not agent:
            raise HTTPException(status_code=404, detail="未找到该Agent")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, data: AgentUpdate):
    """更新Agent配置"""
    try:
        update_data = data.model_dump(exclude_unset=True)
        success = config_service.update_agent(agent_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该Agent")
        return {"message": "更新成功", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Agent配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_code}/prompt", response_model=AgentPromptResponse)
async def get_agent_prompt(agent_code: str):
    """获取Agent的系统提示词"""
    try:
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


# ==================== 设备管理 ====================

@router.get("/devices", response_model=List[DeviceResponse])
async def get_devices(
    device_type: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """获取设备配置列表"""
    try:
        devices = config_service.get_devices(device_type, is_active)
        return devices
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_code}", response_model=DeviceResponse)
async def get_device(device_code: str):
    """根据代码获取设备配置"""
    try:
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
        accounts = config_service.get_xiaomi_accounts(is_active)
        return accounts
    except Exception as e:
        logger.error(f"获取小米账号配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xiaomi-accounts/default", response_model=XiaomiAccountResponse)
async def get_default_xiaomi_account():
    """获取默认小米账号"""
    try:
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
        configs = config_service.get_system_configs(category)
        return configs
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-config/{config_key}")
async def get_system_config(config_key: str):
    """根据键获取系统配置值"""
    try:
        value = config_service.get_system_config(config_key)
        if value is None:
            raise HTTPException(status_code=404, detail="未找到该配置项")
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
        success = config_service.update_system_config(config_key, data.config_value)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败或未找到该配置项")
        return {"message": "更新成功", "config_key": config_key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

