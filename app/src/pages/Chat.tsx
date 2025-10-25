import { Sender, Bubble } from "@ant-design/x";
import { RobotOutlined, UserOutlined } from "@ant-design/icons";
import { App, Flex } from "antd";
import React, { useState, useEffect } from "react";
import "./style/chat.sass";
import { sendChatMessage } from "../api/chat";

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
  role: 'user' | 'ai';
  content: string;
}

const Chat: React.FC = () => {
  const [value, setValue] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  // 移除 useBackend 状态，只使用后端接口
  const { message } = App.useApp();
  const contextId = React.useRef<string>(`session-${Date.now()}`);

  useEffect(() => {
    setIsConnected(true);
  }, []);

  // 发送消息
  const sendMessage = async (userMessage: string) => {
    try {
      setLoading(true);
      
      // 添加用户消息
      const userMsg: Message = {
        key: messages.length,
        role: 'user',
        content: userMessage,
      };
      setMessages(prev => [...prev, userMsg]);

      // 通过 FastAPI 后端发送
      const response = await sendChatMessage(userMessage, contextId.current);
      const content = response.content;
      // 更新 context_id（如果后端返回了新的）
      if (response.context_id) {
        contextId.current = response.context_id;
      }
      
      // 添加 AI 回复
      const aiMsg: Message = {
        key: messages.length + 1,
        role: 'ai',
        content,
      };
      setMessages(prev => [...prev, aiMsg]);
      
    } catch (error: any) {
      console.error('发送消息失败:', error);
      message.error(error.message || "发送消息失败！");
      
      // 添加错误消息
      const errorMsg: Message = {
        key: messages.length + 1,
        role: 'ai',
        content: `❌ ${error.message || '抱歉，处理您的请求时出现问题。'}`,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="chat-container">
      <Bubble
        placement="start"
        content="您好！我是 Moss AI 智能家居助手，可以帮您控制和管理所有智能设备。您可以试试：
        
• 查看所有可用代理
• 打开空调并设置温度为26度
• 查看空气质量
• 打开床头灯
• 分析我的使用习惯"
        avatar={{
          icon: <RobotOutlined />,
          style: aiAvatar,
        }}
      />
      {messages.length > 0 && (
        <div style={{ maxHeight: 500, paddingInline: 16 }}>
          {messages.map((msg) => (
            <Bubble
              key={msg.key}
              placement={msg.role === 'ai' ? 'start' : 'end'}
              content={msg.content}
              avatar={{
                icon: msg.role === 'ai' ? <RobotOutlined /> : <UserOutlined />,
                style: msg.role === 'ai' ? aiAvatar : userAvatar,
              }}
            />
          ))}
        </div>
      )}
      <Flex className="chat-input-container">
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
            if (!isConnected) {
              message.error("后端服务未连接，请先启动服务！");
              return;
            }
            const userMessage = value;
            setValue("");
            sendMessage(userMessage);
          }}
          onCancel={() => {
            setLoading(false);
            message.error("取消发送！");
          }}
          autoSize={{ minRows: 2, maxRows: 6 }}
          placeholder="输入您的消息..."
        />
      </Flex>
    </div>
  );
};

export default Chat;
