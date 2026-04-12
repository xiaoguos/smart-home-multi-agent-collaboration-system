import { Sender, Bubble } from "@ant-design/x";
import { 
  RobotOutlined, 
  UserOutlined, 
  CopyOutlined, 
  ReloadOutlined,
  PlusOutlined,
  MessageOutlined,
  DeleteOutlined,
  EditOutlined
} from "@ant-design/icons";
import { App, Button, Space, Alert, List, Typography, Drawer, Tooltip, Spin, Input, Modal, Select, Tag } from "antd";
import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import "./chat.sass";
import { sendChatMessage } from "../../api/chat";
import { checkBindingStatus } from "../../api/xiaomi";
import { getAgents, type Agent } from "../../api/config";
import {
  getConversationList,
  getConversationHistory,
  updateConversation,
  deleteConversation,
  Conversation,
  ChatMessage,
} from "../../api/conversation";

const { Text } = Typography;

const userAvatar: React.CSSProperties = {
  color: "#1890ff",
  backgroundColor: "#e6f7ff",
};

const aiAvatar: React.CSSProperties = {
  color: "#52c41a",
  backgroundColor: "#f6ffed",
};

interface Message {
  key: number;
  role: "user" | "ai";
  content: string;
}

const Chat: React.FC = () => {
  const navigate = useNavigate();
  const [value, setValue] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isBound, setIsBound] = useState<boolean>(true);
  const [checkingBinding, setCheckingBinding] = useState<boolean>(true);
  const { message } = App.useApp();
  const contextId = React.useRef<string>(`session-${Date.now()}`);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // 对话列表相关状态
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false); // 默认不打开抽屉
  const [conversationsLoading, setConversationsLoading] = useState<boolean>(false);
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>("");
  const [isTemporaryConversation, setIsTemporaryConversation] = useState<boolean>(false); // 标记是否为临时对话
  const [enabledAgents, setEnabledAgents] = useState<Agent[]>([]);
  const [selectedAgentCode, setSelectedAgentCode] = useState<string>("conductor");
  const [conversationAgentMap, setConversationAgentMap] = useState<Record<string, string>>({});
  const [createConversationModalOpen, setCreateConversationModalOpen] = useState<boolean>(false);
  const [newConversationAgentCode, setNewConversationAgentCode] = useState<string>("");

  // 滚动到底部
  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  // 当消息更新时自动滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 获取用户ID（安全版本，不抛出异常）
  const getUserId = (): number | null => {
    try {
      const userStr = localStorage.getItem('user_info');
      if (!userStr) {
        return null;
      }
      const user = JSON.parse(userStr);
      return user.id || null;
    } catch (error) {
      console.error('获取用户ID失败:', error);
      return null;
    }
  };

  const getAgentName = (agentCode?: string): string => {
    if (!agentCode) {
      return "未选择";
    }
    const matched = enabledAgents.find((agent) => agent.agent_code === agentCode);
    return matched?.agent_name || agentCode;
  };

  const isEnabledAgentCode = (agentCode?: string): agentCode is string => {
    if (!agentCode) {
      return false;
    }
    return enabledAgents.some((agent) => agent.agent_code === agentCode);
  };

  const getDefaultAgentCode = (): string => {
    if (isEnabledAgentCode(selectedAgentCode)) {
      return selectedAgentCode;
    }
    const preferred = enabledAgents.find((agent) => agent.agent_code === "conductor");
    return preferred?.agent_code || enabledAgents[0]?.agent_code || "";
  };

  const getConversationAgentCode = (conversation?: Conversation | null): string => {
    if (!conversation) {
      return selectedAgentCode;
    }
    return conversationAgentMap[conversation.context_id] || selectedAgentCode;
  };

  const hydrateConversationAgentMap = async (
    conversationList: Conversation[],
    userId: number,
  ): Promise<void> => {
    const missingContextIds = conversationList
      .map((conversation) => conversation.context_id)
      .filter((context) => !conversationAgentMap[context]);

    if (!missingContextIds.length) {
      return;
    }

    const agentResults = await Promise.allSettled(
      missingContextIds.map(async (context) => {
        const historyResponse = await getConversationHistory(context, {
          system_user_id: userId,
          limit: 1,
        });
        const latestMessage = historyResponse.data?.[0];
        const latestAgentCode = latestMessage?.metadata?.agent_code;
        if (typeof latestAgentCode !== "string" || !latestAgentCode.trim()) {
          return null;
        }
        return {
          context,
          agentCode: latestAgentCode.trim(),
        };
      }),
    );

    const nextMap: Record<string, string> = {};
    agentResults.forEach((result) => {
      if (result.status === "fulfilled" && result.value) {
        nextMap[result.value.context] = result.value.agentCode;
      }
    });

    if (Object.keys(nextMap).length > 0) {
      setConversationAgentMap((prev) => ({
        ...prev,
        ...nextMap,
      }));
    }
  };

  const loadEnabledAgents = async () => {
    try {
      const agents = await getAgents(true);
      setEnabledAgents(agents);

      if (!agents.length) {
        setSelectedAgentCode("");
        setNewConversationAgentCode("");
        return;
      }

      const hasCurrentSelected = agents.some((agent) => agent.agent_code === selectedAgentCode);
      const hasNewConversationSelected = agents.some(
        (agent) => agent.agent_code === newConversationAgentCode,
      );
      const preferred = agents.find((agent) => agent.agent_code === "conductor");
      const fallbackAgentCode = preferred?.agent_code || agents[0].agent_code;
      if (!hasCurrentSelected) {
        setSelectedAgentCode(fallbackAgentCode);
      }
      if (!hasNewConversationSelected) {
        setNewConversationAgentCode(fallbackAgentCode);
      }
    } catch (error) {
      console.error("加载可用Agent失败:", error);
      setEnabledAgents([]);
      setSelectedAgentCode("");
      setNewConversationAgentCode("");
      message.error("加载可用Agent失败");
    }
  };

  // 加载对话列表
  const loadConversations = async (autoSelectFirst: boolean = false): Promise<Conversation[]> => {
    try {
      setConversationsLoading(true);
      const userId = getUserId();
      
      if (!userId) {
        message.warning("未找到用户信息");
        return [];
      }
      
      const response = await getConversationList({
        system_user_id: userId,
        limit: 50,
        only_active: true
      });
      
      const latestConversations = response.data || [];
      setConversations(latestConversations);
      void hydrateConversationAgentMap(latestConversations, userId);
      
      // 只在明确要求时才自动选择第一个
      if (autoSelectFirst && latestConversations.length > 0 && !currentConversation) {
        await switchConversation(latestConversations[0]);
      }
      return latestConversations;
    } catch (error) {
      console.error("加载对话列表失败:", error);
      message.error("加载对话列表失败");
      return [];
    } finally {
      setConversationsLoading(false);
    }
  };
  
  // 创建新对话（清空当前对话，准备开始新的对话）
  const createTemporaryConversation = (agentCode?: string) => {
    // 清空 context_id，下次发送消息时后端会创建新对话
    contextId.current = "";
    setIsTemporaryConversation(true);
    setMessages([]); // 清空消息
    setCurrentConversation(null); // 清空当前对话
    if (agentCode) {
      setSelectedAgentCode(agentCode);
    }
  };

  const openCreateConversationModal = () => {
    if (!enabledAgents.length) {
      message.warning("当前没有可用Agent，请先在配置页启用Agent");
      return;
    }
    setNewConversationAgentCode(getDefaultAgentCode());
    setCreateConversationModalOpen(true);
  };

  // 创建新对话（临时的，不存数据库）
  const handleCreateConversation = () => {
    const targetAgentCode = newConversationAgentCode || getDefaultAgentCode();
    if (!isEnabledAgentCode(targetAgentCode)) {
      message.warning("请选择可用的Agent后再新建对话");
      return;
    }

    createTemporaryConversation(targetAgentCode);
    setCreateConversationModalOpen(false);
    message.success(`创建新对话，当前Agent：${getAgentName(targetAgentCode)}`);
  };

  // 切换对话
  const switchConversation = async (conversation: Conversation) => {
    try {
      const targetContextId = conversation.context_id;
      
      // 关闭抽屉
      setDrawerOpen(false);
      
      const userId = getUserId();
      if (!userId) {
        message.error("未找到用户信息");
        setMessages([]);
        return;
      }
      
      // 1. 刷新对话列表，获取最新的对话元数据
      const listResponse = await getConversationList({
        system_user_id: userId,
        limit: 50,
        only_active: true
      });
      setConversations(listResponse.data);
      
      // 从最新列表中找到当前对话
      const updatedConversation = listResponse.data.find(
        (c: Conversation) => c.context_id === targetContextId,
      );
      setCurrentConversation(updatedConversation || conversation);
      contextId.current = targetContextId;
      setIsTemporaryConversation(false);

      const rememberedAgentCode = conversationAgentMap[targetContextId];
      if (isEnabledAgentCode(rememberedAgentCode)) {
        setSelectedAgentCode(rememberedAgentCode);
      } else {
        setSelectedAgentCode(getDefaultAgentCode());
      }
      
      // 2. 加载对话的历史消息
      const historyResponse = await getConversationHistory(targetContextId, {
        system_user_id: userId,
        limit: 100
      });
      
      // 转换并显示历史消息
      if (historyResponse.data && Array.isArray(historyResponse.data)) {
        const historyMessages: Message[] = historyResponse.data
          .filter(
            (msg: ChatMessage) => msg.role === "user" || msg.role === "agent",
          )
          .map((msg: ChatMessage, index: number) => ({
            key: index,
            role: msg.role === 'agent' ? 'ai' : 'user',
            content: msg.content
          }));
        
        setMessages(historyMessages);

        const latestWithAgent = [...historyResponse.data]
          .reverse()
          .find((msg: ChatMessage) => Boolean(msg.metadata?.agent_code));
        const latestAgentCode = latestWithAgent?.metadata?.agent_code;
        if (typeof latestAgentCode === "string" && latestAgentCode.trim()) {
          const normalizedLatestAgentCode = latestAgentCode.trim();
          setConversationAgentMap((prev) => ({
            ...prev,
            [targetContextId]: normalizedLatestAgentCode,
          }));
          if (isEnabledAgentCode(normalizedLatestAgentCode)) {
            setSelectedAgentCode(normalizedLatestAgentCode);
          }
        }
      } else {
        setMessages([]);
      }
    } catch (error) {
      console.error("切换对话失败:", error);
      message.error("加载对话历史失败");
      setMessages([]);
    }
  };

  // 删除对话
  const handleDeleteConversation = async (conversation: Conversation) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除对话"${conversation.title}"吗？`,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          const userId = getUserId();
          if (!userId) {
            message.error("未找到用户信息，无法删除对话");
            return;
          }
          
          await deleteConversation({
            context_id: conversation.context_id,
            system_user_id: userId
          });
          
          // 如果删除的是当前对话，创建新对话
          if (currentConversation?.context_id === conversation.context_id) {
            createTemporaryConversation(getDefaultAgentCode());
          }
          
          // 刷新对话列表
          await loadConversations();
          message.success("删除对话成功");
        } catch (error) {
          console.error("删除对话失败:", error);
          message.error("删除对话失败");
        }
      }
    });
  };

  // 编辑对话标题
  const handleSaveTitle = async (conversationId: string) => {
    try {
      // 更新数据库中的对话标题
      await updateConversation({
        context_id: conversationId,
        title: editingTitle
      });
      
      setEditingConversationId(null);
      await loadConversations();
      message.success("修改标题成功");
    } catch (error) {
      console.error("修改标题失败:", error);
      message.error("修改标题失败");
    }
  };

  // 检查小米账号绑定状态
  useEffect(() => {
    const checkBinding = async () => {
      try {
        // 从 localStorage 获取用户信息
        const userStr = localStorage.getItem('user_info');
        if (!userStr) {
          setIsBound(false);
          setCheckingBinding(false);
          return;
        }
        
        const user = JSON.parse(userStr);
        const response = await checkBindingStatus(user.id);
        setIsBound(response.is_bound);
      } catch (error) {
        console.error("检查绑定状态失败:", error);
        // 检查失败时假定已绑定，避免误报
        setIsBound(true);
      } finally {
        setCheckingBinding(false);
      }
    };

    checkBinding();
  }, []);

  // 加载可用Agent（仅启用状态）
  useEffect(() => {
    void loadEnabledAgents();
  }, []);

  // 初始化时加载对话列表，选择最近的对话或创建新对话
  useEffect(() => {
    const initConversations = async () => {
      const userId = getUserId();
      
      if (!userId) {
        createTemporaryConversation(getDefaultAgentCode());
        return;
      }
      
      try {
        const latestConversations = await loadConversations(false);
        if (latestConversations.length > 0) {
          // 有对话记录，选择最近的一个（第一个）
          const latestConversation = latestConversations[0];
          await switchConversation(latestConversation);
        } else {
          // 没有对话记录，创建临时对话
          createTemporaryConversation(getDefaultAgentCode());
        }
      } catch {
        createTemporaryConversation(getDefaultAgentCode());
      }
    };
    
    initConversations();
  }, []);

  // 复制消息内容
  const copyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      message.success("已复制到剪贴板");
    } catch (error) {
      console.error('复制失败:', error);
      message.error("复制失败");
    }
  };

  // 重新发送消息
  const resendMessage = async (originalMessage: string) => {
    try {
      await sendMessage(originalMessage);
    } catch (error) {
      console.error('重新发送失败:', error);
    }
  };

  // 发送消息
  const sendMessage = async (userMessage: string) => {
    try {
      const activeAgentCode = selectedAgentCode.trim();
      if (!activeAgentCode) {
        message.warning("当前没有可用Agent，请先在配置页启用Agent");
        return;
      }
      if (!enabledAgents.some((agent) => agent.agent_code === activeAgentCode)) {
        message.warning("所选Agent不可用，正在刷新可用列表");
        await loadEnabledAgents();
        return;
      }

      setLoading(true);
      
      // 创建 AbortController 用于取消请求
      abortControllerRef.current = new AbortController();

      // 添加用户消息
      const userMsg: Message = {
        key: messages.length,
        role: "user",
        content: userMessage,
      };
      setMessages((prev) => [...prev, userMsg]);

      // 获取用户 ID
      const systemUserId = getUserId();
      if (!systemUserId) {
        message.error('未找到用户信息，请重新登录');
        return;
      }

      // 通过 FastAPI 后端发送
      const response = await sendChatMessage(
        userMessage, 
        systemUserId, 
        contextId.current,
        activeAgentCode,
        abortControllerRef.current.signal
      );
      const content = response.content;
      const responseAgentCode = response.agent_code?.trim() || activeAgentCode;
      // 更新 context_id（如果后端返回了新的）
      if (response.context_id) {
        contextId.current = response.context_id;
        setConversationAgentMap((prev) => ({
          ...prev,
          [response.context_id]: responseAgentCode,
        }));
        if (isEnabledAgentCode(responseAgentCode)) {
          setSelectedAgentCode(responseAgentCode);
        }
        
        // 如果是临时对话，发送第一条消息后转为正式对话
        if (isTemporaryConversation) {
          const newContextId = response.context_id;
          setIsTemporaryConversation(false);
          
          // 延迟500ms后重新加载对话列表，确保后端已经创建了对话记录
          setTimeout(async () => {
            const latestConversations = await loadConversations(false);
            const newConversation = latestConversations.find(
              (conversation) => conversation.context_id === newContextId,
            );
            if (newConversation) {
              setCurrentConversation(newConversation);
            }
          }, 500);
        }
      }

      // 添加 AI 回复
      const aiMsg: Message = {
        key: messages.length + 1,
        role: "ai",
        content,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error: any) {
      console.error("发送消息失败:", error);
      
      // 检查是否是用户主动取消
      if (error.name === 'AbortError') {
        // 用户取消发送，添加取消消息
        const cancelMsg: Message = {
          key: messages.length + 1,
          role: "ai",
          content: "❌ 消息发送已取消",
        };
        setMessages((prev) => [...prev, cancelMsg]);
        message.info("消息发送已取消");
      } else {
        message.error(error.message || "发送消息失败！");
        // 添加错误消息
        const errorMsg: Message = {
          key: messages.length + 1,
          role: "ai",
          content: `❌ ${error.message || "抱歉，处理您的请求时出现问题。"}`,
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };
  // 配置角色默认属性
  const roles = {
    ai: {
      placement: "start" as const,
      avatar: {
        icon: <RobotOutlined />,
        style: aiAvatar,
      },
    },
    user: {
      placement: "end" as const,
      avatar: {
        icon: <UserOutlined />,
        style: userAvatar,
      },
    },
  };

  // 渲染消息内容（支持Markdown）
  const renderMessageContent = (content: string, role: string): React.ReactNode => {
    if (role === "ai") {
      // AI消息使用Markdown渲染
      const MarkdownComponent = Markdown as any;
      return (
        <div className="markdown-content">
          <MarkdownComponent remarkPlugins={[remarkGfm]}>
            {content}
          </MarkdownComponent>
        </div>
      );
    }
    // 用户消息保持纯文本
    return content;
  };

  const currentConversationAgentCode = getConversationAgentCode(currentConversation);
  const currentConversationAgentName = getAgentName(currentConversationAgentCode);

  // 构建气泡列表数据
  const bubbleItems = [
    {
      key: "welcome",
      role: "ai",
      content: renderMessageContent(
        `您好！当前正在与 ${currentConversationAgentName} 对话，我可以帮您控制和管理智能设备。`,
        "ai",
      ),
    },
    ...messages.map((msg, index) => {
      const item: any = {
        key: msg.key,
        role: msg.role,
        content: renderMessageContent(msg.content, msg.role),
      };

      // 为所有消息添加复制按钮
      if (msg.role === "ai") {
        // AI 消息：复制按钮 + 重新发送按钮
        const userMessageIndex = messages.findIndex((m, i) => i < index && m.role === "user");
        const userMessage = userMessageIndex >= 0 ? messages[userMessageIndex].content : '';
        
        item.footer = (
          <Space size="small">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => copyMessage(msg.content)}
            />
            {userMessage && (
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => resendMessage(userMessage)}
                loading={loading}
              />
            )}
          </Space>
        );
      } else if (msg.role === "user") {
        // 用户消息：只有复制按钮
        item.footer = (
          <Space size="small">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => copyMessage(msg.content)}
            />
          </Space>
        );
      }

      return item;
    }),
  ];

  return (
    <div className="chat-container">
      {/* 对话列表侧边栏 */}
      <Drawer
        title={
          <Space>
            <MessageOutlined />
            <span>对话列表</span>
          </Space>
        }
        placement="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={300}
        styles={{ body: { padding: 0 } }}
        extra={
          <Tooltip title="新建对话">
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={openCreateConversationModal}
            />
          </Tooltip>
        }
      >
        <Spin spinning={conversationsLoading}>
          <List
            dataSource={conversations}
            renderItem={(conv) => (
              <List.Item
                key={conv.context_id}
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  backgroundColor: currentConversation?.context_id === conv.context_id ? '#e6f7ff' : 'transparent',
                }}
                onClick={() => switchConversation(conv)}
                actions={[
                  <Tooltip title="编辑标题" key="edit">
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingConversationId(conv.context_id);
                        setEditingTitle(conv.title);
                      }}
                    />
                  </Tooltip>,
                  <Tooltip title="删除对话" key="delete">
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conv);
                      }}
                    />
                  </Tooltip>,
                ]}
              >
                <List.Item.Meta
                  title={
                    editingConversationId === conv.context_id ? (
                      <Input
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onPressEnter={() => handleSaveTitle(conv.context_id)}
                        onBlur={() => handleSaveTitle(conv.context_id)}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        size="small"
                      />
                    ) : (
                      <Text strong>{conv.title}</Text>
                    )
                  }
                  description={
                    <div>
                      {conversationAgentMap[conv.context_id] && (
                        <Tag color="blue" style={{ marginBottom: 6 }}>
                          {getAgentName(conversationAgentMap[conv.context_id])}
                        </Tag>
                      )}
                      <Text type="secondary" ellipsis style={{ fontSize: 12 }}>
                        {conv.last_message || '暂无消息'}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {conv.message_count} 条消息 · {new Date(conv.updated_at).toLocaleDateString()}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Spin>
      </Drawer>

      <Modal
        title="新建对话"
        open={createConversationModalOpen}
        onOk={handleCreateConversation}
        onCancel={() => setCreateConversationModalOpen(false)}
        okText="开始对话"
        cancelText="取消"
        destroyOnClose
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text type="secondary">请选择这个新对话要使用的 Agent</Text>
          <Select
            value={newConversationAgentCode || undefined}
            onChange={(code) => setNewConversationAgentCode(code)}
            options={enabledAgents.map((agent) => ({
              value: agent.agent_code,
              label: `${agent.agent_name} (${agent.agent_code})`,
            }))}
            placeholder="选择Agent"
            style={{ width: "100%" }}
          />
        </Space>
      </Modal>

      {/* 主聊天区域 */}
      <div className="chat-main">
        {/* 当前对话标题栏 */}
        <div className="chat-header">
          <div className="chat-header-left">
            <MessageOutlined style={{ color: '#1890ff' }} />
            <Text strong style={{ fontSize: 16 }}>
              {currentConversation?.title || "新对话"}
            </Text>
          </div>

          <div className="chat-header-center">
            <Tag color="blue">当前Agent：{currentConversationAgentName}</Tag>
          </div>

          <div className="chat-header-right">
            <Text type="secondary" style={{ fontSize: 12 }}>
              {currentConversation ? `${currentConversation.message_count} 条消息` : "临时会话"}
            </Text>
          </div>
        </div>
        
        {/* 小米账号绑定提示 */}
        {!checkingBinding && !isBound && (
          <div style={{ padding: "16px 16px 0", flexShrink: 0 }}>
            <Alert
              message="需要绑定小米账号"
              description="要使用智能家居控制功能，请先绑定您的小米账号。"
              type="warning"
              showIcon
              action={
                <Button size="small" type="primary" onClick={() => navigate("/xiaomi-binding")}>
                  立即绑定
                </Button>
              }
              closable
            />
          </div>
        )}

        {enabledAgents.length === 0 && (
          <div style={{ padding: "16px 16px 0", flexShrink: 0 }}>
            <Alert
              message="当前没有可用Agent"
              description="请前往设置页启用至少一个Agent后再发起对话。"
              type="warning"
              showIcon
            />
          </div>
        )}
        
        {/* 消息区域 - 可滚动 */}
        <div className="chat-messages" ref={messagesContainerRef}>
          <Bubble.List
            autoScroll={true}
            items={bubbleItems}
            roles={roles}
          />
        </div>
        
        {/* 输入区域 - 固定在底部 */}
        <div className="chat-input-container">
          {!drawerOpen && (
            <Button
              type="primary"
              icon={<MessageOutlined />}
              onClick={() => {
                setDrawerOpen(true);
                loadConversations(false);
              }}
              style={{
                marginBottom: 16,
              }}
            >
              对话列表
            </Button>
          )}
          <Sender
            className="chat-input"
            loading={loading}
            value={value}
            onChange={(v) => {
              setValue(v);
            }}
            onSubmit={() => {
              if (!value.trim()) {
                message.warning("请输入消息内容！");
                return;
              }
              if (!selectedAgentCode) {
                message.warning("请先选择可用Agent");
                return;
              }
              const userMessage = value;
              setValue("");
              sendMessage(userMessage);
            }}
            onCancel={() => {
              if (abortControllerRef.current) {
                abortControllerRef.current.abort();
              }
              setLoading(false);
            }}
            autoSize={{ minRows: 2, maxRows: 6 }}
            placeholder={selectedAgentCode ? `发消息给 ${getAgentName(selectedAgentCode)}...` : "请先启用并选择Agent"}
          />
        </div>
      </div>
    </div>
  );
};

export default Chat;
