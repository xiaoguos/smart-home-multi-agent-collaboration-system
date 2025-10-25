import axios from 'axios';
import type { A2ARequest, A2AResponse, ChatMessage } from './type/a2a';

// Conductor Agent 的基础 URL
const CONDUCTOR_AGENT_URL = 'http://localhost:12000/';

// 请求ID计数器
let requestIdCounter = 1;

/**
 * 生成唯一的消息ID
 */
function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 提取 A2A 响应中的内容
 * 简单直接地提取所有文本内容，不做复杂处理
 */
function extractContentFromResponse(response: A2AResponse): string {
  try {
    const contents: string[] = [];
    
    // 1. 从 artifacts 中提取所有文本内容
    if (response.result.artifacts && response.result.artifacts.length > 0) {
      response.result.artifacts.forEach(artifact => {
        artifact.parts.forEach(part => {
          if (part.text) {
            contents.push(part.text);
          }
        });
      });
    }
    
    // 2. 如果 artifacts 有内容，直接返回
    if (contents.length > 0) {
      return contents.join('\n\n');
    }
    
    // 3. 否则从 history 中提取 agent 的回复
    const agentMessages = response.result.history
      .filter(item => item.role === 'agent')
      .map(item => 
        item.parts
          .filter(part => part.text)
          .map(part => part.text)
          .join('\n')
      )
      .filter(text => text.trim().length > 0);
    
    if (agentMessages.length > 0) {
      return agentMessages.join('\n\n');
    }
    
    // 4. 兜底：检查任务状态
    if (response.result.status) {
      const state = response.result.status.state;
      if (state === 'completed') return '✅ 任务已完成';
      if (state === 'in_progress') return '⏳ 任务进行中...';
      if (state === 'failed') return '❌ 任务执行失败';
    }
    
    // 5. 实在没内容就返回默认消息
    return '已收到响应';
  } catch (error) {
    console.error('解析响应失败:', error);
    return '❌ 处理响应时出错';
  }
}

/**
 * 发送消息到 Conductor Agent
 * @param userMessage 用户输入的消息
 * @param contextId 会话上下文ID
 * @returns AI 回复的消息
 */
export async function sendMessageToConductor(
  userMessage: string,
  contextId: string
): Promise<ChatMessage> {
  try {
    // 构建 A2A 协议请求
    const request: A2ARequest = {
      jsonrpc: '2.0',
      method: 'message/send',
      params: {
        message: {
          context_id: contextId,
          role: 'user',
          parts: [
            {
              kind: 'text',
              text: userMessage,
            },
          ],
          message_id: generateMessageId(),
        },
      },
      id: requestIdCounter++,
    };

    console.log('📤 发送请求到 Conductor Agent:', request);

    // 发送请求
    const response = await axios.post<A2AResponse>(CONDUCTOR_AGENT_URL, request, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 120000, // 120秒超时
    });

    console.log('📥 收到响应:', response.data);

    // 检查响应状态
    if (response.data.result.status.state === 'failed') {
      throw new Error('任务执行失败');
    }

    // 提取内容
    const content = extractContentFromResponse(response.data);

    return {
      role: 'ai',
      content,
      timestamp: new Date().toISOString(),
    };
  } catch (error: any) {
    console.error('❌ 发送消息失败:', error);
    
    // 处理不同类型的错误
    if (error.code === 'ECONNREFUSED') {
      throw new Error('无法连接到 Conductor Agent，请确保服务已启动 (http://localhost:12000)');
    } else if (error.code === 'ETIMEDOUT') {
      throw new Error('请求超时，Agent 可能正在处理复杂任务');
    } else if (error.response?.data?.error) {
      throw new Error(`Agent 返回错误: ${error.response.data.error.message || '未知错误'}`);
    } else {
      throw new Error(error.message || '发送消息失败');
    }
  }
}

/**
 * 测试 Conductor Agent 连接
 */
export async function testConductorConnection(): Promise<boolean> {
  try {
    const response = await axios.get(`${CONDUCTOR_AGENT_URL}.well-known/agent-card.json`, {
      timeout: 5000,
    });
    
    console.log('✅ Conductor Agent 连接正常:', response.data.name);
    return true;
  } catch (error) {
    console.error('❌ Conductor Agent 连接失败:', error);
    return false;
  }
}

