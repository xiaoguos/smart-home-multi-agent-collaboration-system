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
import { App, Button, Space, Alert, List, Typography, Drawer, Tooltip, Spin, Input, Modal } from "antd";
import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./style/chat.sass";
import { sendChatMessage } from "../api/chat";
import { checkBindingStatus } from "../api/xiaomi";
import {
  getConversationList,
  getConversationHistory,
  updateConversation,
  deleteConversation,
  type Conversation,
} from "../api/conversation";

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

  // 加载对话列表
  const loadConversations = async () => {
    try {
      setConversationsLoading(true);
      const userId = getUserId();
      
      // 如果没有用户ID，创建临时对话
      if (!userId) {
        createTemporaryConversation();
        return;
      }
      
      const response = await getConversationList({
        system_user_id: userId,
        limit: 50,
        only_active: true
      });
      
      setConversations(response.data);
      
      // 如果对话列表为空，创建临时对话
      if (response.data.length === 0) {
        createTemporaryConversation();
      } else if (!currentConversation && !isTemporaryConversation) {
        // 如果有对话列表但没有当前对话（且不是临时对话），选择第一个
        await switchConversation(response.data[0]);
      }
    } catch (error) {
      console.error("加载对话列表失败:", error);
      // 加载失败时也创建临时对话
      createTemporaryConversation();
    } finally {
      setConversationsLoading(false);
    }
  };
  
  // 创建临时对话（前端临时，不存数据库）
  const createTemporaryConversation = () => {
    const tempContextId = `temp-${Date.now()}`;
    contextId.current = tempContextId;
    setIsTemporaryConversation(true);
    setMessages([]); // 清空消息
    
    // 创建临时对话对象，添加到列表顶部显示
    const tempConversation: Conversation = {
      id: Date.now(),
      context_id: tempContextId,
      system_user_id: getUserId() || 0, // 临时对话不需要真实用户ID
      title: "新对话",
      description: undefined,
      message_count: 0,
      last_message: undefined,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_active: true
    };
    
    // 将临时对话添加到列表顶部
    setConversations(prev => [tempConversation, ...prev.filter(c => !c.context_id.startsWith('temp-'))]);
    setCurrentConversation(tempConversation);
  };

  // 创建新对话（临时的，不存数据库）
  const handleCreateConversation = async () => {
    try {
      // 创建临时对话
      createTemporaryConversation();
      message.success("创建新对话");
    } catch (error) {
      console.error("创建对话失败:", error);
      message.error("创建对话失败");
    }
  };

  // 切换对话
  const switchConversation = async (conversation: Conversation) => {
    try {
      setCurrentConversation(conversation);
      contextId.current = conversation.context_id;
      setIsTemporaryConversation(conversation.context_id.startsWith('temp-')); // 根据 context_id 判断是否临时对话
      
      // 如果是临时对话，清空消息列表即可
      if (conversation.context_id.startsWith('temp-')) {
        setMessages([]);
        return;
      }
      
      // 加载历史消息
      const userId = getUserId();
      if (!userId) {
        message.error("未找到用户信息，无法加载历史消息");
        setMessages([]);
        return;
      }
      
      const response = await getConversationHistory(conversation.context_id, {
        system_user_id: userId,
        limit: 100
      });
      
      // 转换为 Message 格式
      const historyMessages: Message[] = response.data
        .filter(msg => msg.role === 'user' || msg.role === 'agent')
        .map((msg, index) => ({
          key: index,
          role: msg.role === 'agent' ? 'ai' : 'user',
          content: msg.content
        }));
      
      setMessages(historyMessages);
    } catch (error) {
      console.error("切换对话失败:", error);
      message.error("加载对话历史失败");
    }
  };

  // 删除对话
  const handleDeleteConversation = async (conversation: Conversation) => {
    // 如果是临时对话，直接从前端删除，不调用后端API
    if (conversation.context_id.startsWith('temp-')) {
      // 从列表中移除临时对话
      setConversations(prev => prev.filter(c => c.context_id !== conversation.context_id));
      
      // 如果删除的是当前对话，创建新的临时对话
      if (currentConversation?.context_id === conversation.context_id) {
        createTemporaryConversation();
      }
      
      message.success("删除临时对话成功");
      return;
    }
    
    // 删除数据库中的对话
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
            handleCreateConversation();
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
      // 如果是临时对话，只在前端更新标题
      if (conversationId.startsWith('temp-')) {
        setConversations(prev => prev.map(c => 
          c.context_id === conversationId 
            ? { ...c, title: editingTitle }
            : c
        ));
        
        // 如果是当前对话，也更新当前对话的标题
        if (currentConversation?.context_id === conversationId) {
          setCurrentConversation(prev => prev ? { ...prev, title: editingTitle } : null);
        }
        
        setEditingConversationId(null);
        message.success("修改标题成功");
        return;
      }
      
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

  // 初始化时加载对话列表
  useEffect(() => {
    loadConversations();
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
        abortControllerRef.current.signal
      );
      const content = response.content;
      // 更新 context_id（如果后端返回了新的）
      if (response.context_id) {
        contextId.current = response.context_id;
        
        // 如果是临时对话，发送第一条消息后自动刷新对话列表
        if (isTemporaryConversation) {
          const newContextId = response.context_id;
          setIsTemporaryConversation(false);
          
          // 延迟刷新，确保后端已经创建了对话记录
          setTimeout(async () => {
            // 移除临时对话
            setConversations(prev => prev.filter(c => !c.context_id.startsWith('temp-')));
            
            // 重新加载对话列表
            try {
              const userId = getUserId();
              if (!userId) {
                console.error("刷新对话列表失败: 未找到用户信息");
                return;
              }
              
              const response = await getConversationList({
                system_user_id: userId,
                limit: 50,
                only_active: true
              });
              
              setConversations(response.data);
              
              // 找到新创建的对话并切换过去
              const newConv = response.data.find(c => c.context_id === newContextId);
              if (newConv) {
                setCurrentConversation(newConv);
              }
            } catch (error) {
              console.error("刷新对话列表失败:", error);
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

  // 构建气泡列表数据
  const bubbleItems = [
    {
      key: "welcome",
      role: "ai",
      content: "您好！我是 Moss AI 智能家居助手，可以帮您控制和管理所有智能设备。",
    },
    ...messages.map((msg, index) => {
      const item: any = {
        key: msg.key,
        role: msg.role,
        content: msg.content,
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
    <div className="chat-container" style={{ display: 'flex', height: '100%' }}>
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
              onClick={handleCreateConversation}
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
                      <Text strong>
                    {conv.title}
                    {conv.context_id.startsWith('temp-') && (
                      <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                        (未保存)
                      </Text>
                    )}
                  </Text>
                    )
                  }
                  description={
                    <div>
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

      {/* 主聊天区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* 切换侧边栏按钮 */}
        {!drawerOpen && (
          <Button
            type="primary"
            icon={<MessageOutlined />}
            onClick={() => setDrawerOpen(true)}
            style={{
              position: 'absolute',
              top: 16,
              left: 16,
              zIndex: 10,
            }}
          >
            对话列表
          </Button>
        )}

        {/* 小米账号绑定提示 */}
        {!checkingBinding && !isBound && (
          <div style={{ padding: "16px 16px 0" }}>
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
        
        <div className="chat-messages" ref={messagesContainerRef} style={{ flex: 1, overflow: 'auto' }}>
          <Bubble.List
            autoScroll={true}
            items={bubbleItems}
            roles={roles}
          />
        </div>
        <div className="chat-input-container">
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
            placeholder="输入您的消息..."
          />
        </div>
      </div>
    </div>
  );
};

export default Chat;
