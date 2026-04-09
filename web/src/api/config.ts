import { httpClient } from '@/utils';

/**
 * 配置管理 API 接口
 */

// ==================== 类型定义 ====================

export interface AIModel {
  id: number;
  model_name: string;
  provider: string;
  api_key: string;
  api_base: string;
  model_type: string;
  temperature: number;
  max_tokens: number;
  is_default: boolean;
  is_active: boolean;
}

export interface Agent {
  id: number;
  agent_code: string;
  agent_name: string;
  host: string;
  port: number;
  description?: string;
  is_enabled: boolean;
}

export interface AgentPrompt {
  agent_code: string;
  prompt_text: string;
}

export interface Device {
  id: number;
  device_code: string;
  device_name: string;
  device_type: string;
  agent_code: string;
  ip_address?: string;
  token?: string;
  model?: string;
  extra_config?: string;
  is_active: boolean;
}

export interface XiaomiAccount {
  id: number;
  username: string;
  password: string;
  region: string;
  is_default: boolean;
  is_active: boolean;
}

export interface SystemConfig {
  id: number;
  config_key: string;
  config_value: string;
  config_type: string;
  category: string;
  description?: string;
  is_active: boolean;
}

// ==================== AI 模型管理 ====================

export async function getAIModels(isActive?: boolean): Promise<AIModel[]> {
  const params = isActive !== undefined ? { is_active: isActive } : {};
  return await httpClient.get('/api/v1/config/ai-models', { params });
}

export async function getAIModel(modelId: number): Promise<AIModel> {
  return await httpClient.get(`/api/v1/config/ai-models/${modelId}`);
}

export async function updateAIModel(
  modelId: number,
  data: Partial<Omit<AIModel, 'id'>>
): Promise<{ message: string; model_id: number }> {
  return await httpClient.put(`/api/v1/config/ai-models/${modelId}`, data);
}

export async function createAIModel(
  data: Omit<AIModel, 'id'>
): Promise<{ message: string; model_id: number }> {
  return await httpClient.post('/api/v1/config/ai-models', data);
}

// ==================== Agent 管理 ====================

export async function getAgents(isEnabled?: boolean): Promise<Agent[]> {
  const params = isEnabled !== undefined ? { is_enabled: isEnabled } : {};
  return await httpClient.get('/api/v1/config/agents', { params });
}

export async function getAgent(agentCode: string): Promise<Agent> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}`);
}

export async function updateAgent(
  agentId: number,
  data: Partial<Omit<Agent, 'id' | 'agent_code'>>
): Promise<{ message: string; agent_id: number }> {
  return await httpClient.put(`/api/v1/config/agents/${agentId}`, data);
}

export async function getAgentPrompt(agentCode: string): Promise<AgentPrompt> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}/prompt`);
}

export async function updateAgentPrompt(
  agentCode: string,
  promptText: string,
  version?: string
): Promise<{ message: string; agent_code: string }> {
  return await httpClient.put(`/api/v1/config/agents/${agentCode}/prompt`, {
    prompt_text: promptText,
    version: version || 'v1.0',
  });
}

// ==================== 设备管理 ====================

export async function getDevices(
  deviceType?: string,
  isActive?: boolean
): Promise<Device[]> {
  const params: any = {};
  if (deviceType) { params.device_type = deviceType }
  if (isActive !== undefined) { params.is_active = isActive }
  return await httpClient.get('/api/v1/config/devices', { params });
}

export async function getDevice(deviceCode: string): Promise<Device> {
  return await httpClient.get(`/api/v1/config/devices/${deviceCode}`);
}

export async function updateDevice(
  deviceId: number,
  data: Partial<Omit<Device, 'id' | 'device_code' | 'device_type' | 'agent_code'>>
): Promise<{ message: string; device_id: number }> {
  return await httpClient.put(`/api/v1/config/devices/${deviceId}`, data);
}

export async function createDevice(
  data: Omit<Device, 'id'>
): Promise<{ message: string; device_id: number }> {
  return await httpClient.post('/api/v1/config/devices', data);
}

// ==================== 小米账号管理 ====================

export async function getXiaomiAccounts(isActive?: boolean): Promise<XiaomiAccount[]> {
  const params = isActive !== undefined ? { is_active: isActive } : {};
  return await httpClient.get('/api/v1/config/xiaomi-accounts', { params });
}

export async function getDefaultXiaomiAccount(): Promise<XiaomiAccount> {
  return await httpClient.get('/api/v1/config/xiaomi-accounts/default');
}

export async function updateXiaomiAccount(
  accountId: number,
  data: Partial<Omit<XiaomiAccount, 'id'>>
): Promise<{ message: string; account_id: number }> {
  return await httpClient.put(`/api/v1/config/xiaomi-accounts/${accountId}`, data);
}

export async function createXiaomiAccount(
  data: Omit<XiaomiAccount, 'id'>
): Promise<{ message: string; account_id: number }> {
  return await httpClient.post('/api/v1/config/xiaomi-accounts', data);
}

// ==================== 系统配置管理 ====================

export async function getSystemConfigs(category?: string): Promise<SystemConfig[]> {
  const params = category ? { category } : {};
  return await httpClient.get('/api/v1/config/system-config', { params });
}

export async function getSystemConfig(
  configKey: string
): Promise<{ config_key: string; config_value: any }> {
  return await httpClient.get(`/api/v1/config/system-config/${configKey}`);
}

export async function updateSystemConfig(
  configKey: string,
  configValue: string
): Promise<{ message: string; config_key: string }> {
  return await httpClient.put(`/api/v1/config/system-config/${configKey}`, {
    config_value: configValue,
  });
}

