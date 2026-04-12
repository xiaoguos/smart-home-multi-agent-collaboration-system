import { httpClient } from '@/utils';

/**
 * 聊天消息接口
 */
export interface ChatRequest {
  query: string;
  system_user_id: number;
  context_id?: string;
  agent_code?: string;
}

export interface ChatResponse {
  content: string;
  context_id: string;
  task_id?: string;
  status: string;
  agent_code: string;
}

/**
 * 发送聊天消息（通过 FastAPI 后端）
 */
export async function sendChatMessage(
  query: string,
  systemUserId: number,
  contextId?: string,
  agentCode: string = 'conductor',
  signal?: AbortSignal
): Promise<ChatResponse> {
  return await httpClient.post<ChatResponse>('/api/v1/chat', {
    query,
    system_user_id: systemUserId,
    context_id: contextId,
    agent_code: agentCode,
  }, { signal });
}