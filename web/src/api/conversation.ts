/**
 * 对话列表管理 API
 */

import { httpClient } from '@/utils';

export interface Conversation {
  id: number;
  context_id: string;
  system_user_id: number;
  title: string;
  description?: string;
  message_count: number;
  last_message?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface ChatMessage {
  id: number;
  system_user_id: number;
  context_id: string;
  message_id?: string;
  task_id?: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  status: 'success' | 'failed' | 'error';
  error_message?: string;
  metadata?: any;
  created_at: string;
}

/**
 * 创建新对话
 */
export const createConversation = async (data: {
  system_user_id: number;
  title?: string;
  description?: string;
}) => {
  return httpClient.post<{
    success: boolean;
    message: string;
    data: Conversation;
  }>('/api/v1/conversations/create', data);
};

/**
 * 获取对话列表
 */
export const getConversationList = async (params: {
  system_user_id: number;
  limit?: number;
  only_active?: boolean;
}) => {
  return httpClient.get<{
    success: boolean;
    message: string;
    data: Conversation[];
    total: number;
  }>('/api/v1/conversations/list', { params });
};

/**
 * 获取对话详情
 */
export const getConversation = async (context_id: string) => {
  return httpClient.get<{
    success: boolean;
    message: string;
    data: Conversation;
  }>(`/api/v1/conversations/${context_id}`);
};

/**
 * 更新对话信息
 */
export const updateConversation = async (data: {
  context_id: string;
  title?: string;
}) => {
  return httpClient.put<{
    success: boolean;
    message: string;
  }>('/api/v1/conversations/update', data);
};

/**
 * 删除对话
 */
export const deleteConversation = async (data: {
  context_id: string;
  system_user_id: number;
}) => {
  return httpClient.delete<{
    success: boolean;
    message: string;
  }>('/api/v1/conversations/delete', { data });
};

/**
 * 获取对话历史消息
 */
export const getConversationHistory = async (
  context_id: string,
  params: {
    system_user_id: number;
    limit?: number;
  }
) => {
  return httpClient.get<{
    success: boolean;
    message: string;
    data: ChatMessage[];
    total: number;
  }>(`/api/v1/conversations/${context_id}/history`, { params });
};

