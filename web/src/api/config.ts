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
  model_id?: number | null;
  model_name?: string | null;
  runtime_status?: string | null;
  runtime_pid?: number | null;
  runtime_host?: string | null;
  runtime_port?: number | null;
  runtime_server_ip?: string | null;
  runtime_started_at?: string | null;
  runtime_stopped_at?: string | null;
}

export interface AgentCreate {
  agent_code: string;
  agent_name: string;
  host: string;
  port: number;
  description?: string;
  is_enabled: boolean;
  runtime_command?: string;
  runtime_cwd?: string;
}

export interface AgentRuntime {
  agent_code: string;
  agent_name?: string;
  status: string;
  pid?: number | null;
  host?: string | null;
  port?: number | null;
  server_ip?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  command?: string | null;
  cwd?: string | null;
  is_running: boolean;
}

export interface AgentPrompt {
  agent_code: string;
  prompt_text: string;
}

export interface AgentModelBinding {
  agent_code: string;
  model_id?: number | null;
  model_name?: string | null;
}

export interface AgentDeviceBinding {
  source: 'xiaomi' | 'custom';
  device_id: string;
  device_name?: string | null;
  model?: string | null;
}

export interface AgentDeviceBindingsResponse {
  agent_code: string;
  bindings: AgentDeviceBinding[];
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

export interface PluginMode {
  plugin_key: string;
  mode: 'enabled' | 'disabled' | 'unused';
  description?: string;
}

export interface CameraPluginConfig {
  source: 'local' | 'remote';
  local_index: number;
  remote_url: string;
}

/** ESP32 音频 MCP（stdio），与账户插件扩展页、Conductor 共用 */
export interface AudioPluginMcpConfig {
  enabled: boolean;
  command: string;
  args: string[];
  cwd: string;
  env: Record<string, string>;
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

/** 按数据库 is_enabled 对齐本地 Agent 子进程（后端启动时也会执行） */
export async function syncAgentRuntimesWithConfig(): Promise<{
  stopped: string[];
  started: string[];
  errors: { agent_code: string; phase: string; error: string }[];
}> {
  return await httpClient.post('/api/v1/config/agents/sync-runtimes-with-config');
}

export async function getAgent(agentCode: string): Promise<Agent> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}`);
}

export interface AgentPluginCatalogItem {
  plugin_key: string;
  mode: string;
  title: string;
  description: string;
  selected: boolean;
  allow_assign: boolean;
}

export interface AgentPluginsBundle {
  agent_code: string;
  plugin_keys: string[] | null;
  effective_plugin_keys: string[];
  catalog: AgentPluginCatalogItem[];
}

export async function getAgentPluginsBundle(agentCode: string): Promise<AgentPluginsBundle> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}/plugins`);
}

export async function replaceAgentPlugins(
  agentCode: string,
  pluginKeys: string[],
): Promise<{ agent_code: string; plugin_keys: string[]; effective_plugin_keys: string[] }> {
  return await httpClient.put(`/api/v1/config/agents/${agentCode}/plugins`, {
    plugin_keys: pluginKeys,
  });
}

export async function updateAgent(
  agentId: number,
  data: Partial<
    Omit<Agent, 'id' | 'agent_code' | 'model_id' | 'model_name'> & {
      runtime_command?: string | null;
      runtime_cwd?: string | null;
    }
  >
): Promise<{ message: string; agent_id: number }> {
  return await httpClient.put(`/api/v1/config/agents/${agentId}`, data);
}

export async function createAgent(
  data: AgentCreate
): Promise<{ message: string; agent_id: number; agent_code: string; runtime: AgentRuntime }> {
  return await httpClient.post('/api/v1/config/agents', data);
}

export async function deleteAgent(
  agentCode: string
): Promise<{ message: string; agent_code: string }> {
  return await httpClient.delete(`/api/v1/config/agents/${agentCode}`);
}

export async function getAgentRuntime(agentCode: string): Promise<AgentRuntime> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}/runtime`);
}

export async function startAgentRuntime(agentCode: string): Promise<AgentRuntime> {
  return await httpClient.post(`/api/v1/config/agents/${agentCode}/runtime/start`);
}

export async function stopAgentRuntime(agentCode: string): Promise<AgentRuntime> {
  return await httpClient.post(`/api/v1/config/agents/${agentCode}/runtime/stop`);
}

export async function getAgentDeviceBindings(agentCode: string): Promise<AgentDeviceBindingsResponse> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}/device-bindings`);
}

export async function replaceAgentDeviceBindings(
  agentCode: string,
  bindings: AgentDeviceBinding[],
  opts?: { systemUserId?: number; server?: string },
): Promise<AgentDeviceBindingsResponse> {
  return await httpClient.put(`/api/v1/config/agents/${agentCode}/device-bindings`, {
    bindings,
    system_user_id: opts?.systemUserId,
    server: opts?.server ?? 'cn',
  });
}

/** 按米家在线状态自动禁用「所绑米家设备全部离线」的 Agent */
export async function syncAgentDeviceOfflinePolicy(
  systemUserId: number,
  server: string = 'cn',
): Promise<{ disabled_count: number }> {
  return await httpClient.post('/api/v1/config/agents/sync-device-offline-policy', undefined, {
    params: { system_user_id: systemUserId, server },
  });
}

export async function bindAgentDevice(
  agentCode: string,
  binding: AgentDeviceBinding,
): Promise<AgentDeviceBindingsResponse> {
  return await httpClient.post(`/api/v1/config/agents/${agentCode}/device-bindings`, binding);
}

export async function unbindAgentDevice(
  agentCode: string,
  source: AgentDeviceBinding['source'],
  deviceId: string,
): Promise<AgentDeviceBindingsResponse> {
  return await httpClient.delete(`/api/v1/config/agents/${agentCode}/device-bindings`, {
    params: {
      source,
      device_id: deviceId,
    },
  });
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

export async function getAgentModelBinding(agentCode: string): Promise<AgentModelBinding> {
  return await httpClient.get(`/api/v1/config/agents/${agentCode}/model-binding`);
}

export async function updateAgentModelBinding(
  agentCode: string,
  modelId?: number | null,
): Promise<{ message: string; agent_code: string }> {
  return await httpClient.put(`/api/v1/config/agents/${agentCode}/model-binding`, {
    model_id: modelId ?? null,
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

export async function getLocalIpv4(): Promise<{ ipv4: string }> {
  return await httpClient.get('/api/v1/config/local-ipv4');
}

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

export async function getPluginModes(): Promise<PluginMode[]> {
  return await httpClient.get('/api/v1/config/plugins/modes');
}

export async function updatePluginMode(
  pluginKey: string,
  mode: PluginMode['mode'],
): Promise<PluginMode> {
  return await httpClient.put(`/api/v1/config/plugins/${pluginKey}/mode`, { mode });
}

export async function getCameraPluginConfig(): Promise<CameraPluginConfig> {
  return await httpClient.get('/api/v1/config/plugins/camera/config');
}

export async function updateCameraPluginConfig(
  data: CameraPluginConfig,
): Promise<CameraPluginConfig> {
  return await httpClient.put('/api/v1/config/plugins/camera/config', data);
}

export async function getAudioPluginMcpConfig(): Promise<AudioPluginMcpConfig> {
  return await httpClient.get('/api/v1/config/plugins/audio/mcp-config');
}

export async function updateAudioPluginMcpConfig(
  data: AudioPluginMcpConfig,
): Promise<AudioPluginMcpConfig> {
  return await httpClient.put('/api/v1/config/plugins/audio/mcp-config', data);
}

export interface AudioPluginTestOutputRequest {
  sample_rate?: number;
  channels?: number;
  tool_name?: string | null;
}

export interface AudioPluginTestOutputResponse {
  success: boolean;
  message: string;
  tool_name?: string | null;
  mcp?: Record<string, unknown> | null;
}

export async function testAudioPluginOutput(
  data?: AudioPluginTestOutputRequest,
): Promise<AudioPluginTestOutputResponse> {
  return await httpClient.post('/api/v1/config/plugins/audio/test-output', data ?? {});
}

