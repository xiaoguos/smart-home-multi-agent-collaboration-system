// A2A 协议类型定义

export interface A2AMessagePart {
  kind: string;
  text: string;
}

export interface A2AMessage {
  context_id: string;
  role: 'user' | 'agent';
  parts: A2AMessagePart[];
  message_id: string;
  taskId?: string;
}

export interface A2AHistoryItem {
  contextId: string;
  kind: string;
  messageId: string;
  parts: A2AMessagePart[];
  role: 'user' | 'agent';
  taskId: string;
}

export interface A2AArtifact {
  artifactId: string;
  name: string;
  parts: A2AMessagePart[];
}

export interface A2ATaskStatus {
  state: 'pending' | 'in_progress' | 'completed' | 'failed';
  timestamp: string;
}

export interface A2AResult {
  artifacts?: A2AArtifact[];
  contextId: string;
  history: A2AHistoryItem[];
  id: string;
  kind: string;
  status: A2ATaskStatus;
}

export interface A2AResponse {
  id: number;
  jsonrpc: string;
  result: A2AResult;
}

export interface A2ARequest {
  jsonrpc: string;
  method: string;
  params: {
    message: A2AMessage;
  };
  id: number;
}

// 简化的聊天消息类型
export interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  timestamp?: string;
}

