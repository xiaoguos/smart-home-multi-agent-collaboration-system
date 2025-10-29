import { Sender, Bubble } from "@ant-design/x";
import { RobotOutlined, UserOutlined, CopyOutlined, ReloadOutlined } from "@ant-design/icons";
import { App, Button, Space, Alert } from "antd";
import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./style/chat.sass";
import { sendChatMessage } from "../api/chat";
import { checkBindingStatus } from "../api/xiaomi";

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

      // 通过 FastAPI 后端发送
      const response = await sendChatMessage(userMessage, contextId.current, abortControllerRef.current.signal);
      const content = response.content;
      // 更新 context_id（如果后端返回了新的）
      if (response.context_id) {
        contextId.current = response.context_id;
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
    <div className="chat-container">
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
      
      <div className="chat-messages" ref={messagesContainerRef}>
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
  );
};

export default Chat;
