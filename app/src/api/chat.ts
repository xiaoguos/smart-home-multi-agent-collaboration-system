import { httpClient } from '../utils/request';

/**
 * 聊天消息接口
 */
export interface ChatRequest {
  query: string;
  context_id?: string;
}

export interface ChatResponse {
  content: string;
  context_id: string;
  task_id?: string;
  status: string;
}

/**
 * 发送聊天消息（通过 FastAPI 后端）
 */
export async function sendChatMessage(
  query: string,
  contextId?: string,
  signal?: AbortSignal
): Promise<ChatResponse> {
  return await httpClient.post<ChatResponse>('/api/v1/chat', {
    query,
    context_id: contextId,
  }, { signal });
}