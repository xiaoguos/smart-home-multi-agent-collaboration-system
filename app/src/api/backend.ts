/**
 * FastAPI 后端服务接口
 */

import axios from 'axios';

// 后端 API URL
const BACKEND_API_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:2100';

// 配置 axios 实例
const backendClient = axios.create({
  baseURL: BACKEND_API_URL,
  timeout: 120000, // 120 秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
backendClient.interceptors.request.use(
  (config) => {
    console.log('📤 发送请求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ 请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
backendClient.interceptors.response.use(
  (response) => {
    console.log('📥 收到响应:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('❌ 响应错误:', error.message);
    return Promise.reject(error);
  }
);

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
  contextId?: string
): Promise<ChatResponse> {
  try {
    const response = await backendClient.post<ChatResponse>('/api/chat', {
      query,
      context_id: contextId,
    });

    return response.data;
  } catch (error: any) {
    // 处理错误
    if (error.code === 'ECONNREFUSED') {
      throw new Error('无法连接到后端服务，请确保后端已启动 (http://127.0.0.1:2100)');
    } else if (error.code === 'ETIMEDOUT') {
      throw new Error('请求超时');
    } else if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      throw new Error(detail.message || detail || '请求失败');
    } else {
      throw new Error(error.message || '发送消息失败');
    }
  }
}

/**
 * 检查后端服务健康状态
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await backendClient.get('/health', { timeout: 5000 });
    console.log('✅ 后端服务连接正常:', response.data);
    return true;
  } catch (error) {
    console.error('❌ 后端服务连接失败:', error);
    return false;
  }
}

/**
 * 检查聊天服务健康状态
 */
export async function checkChatHealth(): Promise<boolean> {
  try {
    const response = await backendClient.get('/api/chat/health', { timeout: 5000 });
    console.log('✅ 聊天服务连接正常:', response.data);
    return response.data.conductor_agent === 'connected';
  } catch (error) {
    console.error('❌ 聊天服务连接失败:', error);
    return false;
  }
}

