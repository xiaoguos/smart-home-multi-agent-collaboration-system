import { Sender, Bubble } from "@ant-design/x";
import { RobotOutlined, UserOutlined } from "@ant-design/icons";
import { App, Flex } from "antd";
import React, { useState } from "react";
import "./style/chat.sass";
import axios from "axios";

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
  const { message } = App.useApp();
  const contextId = React.useRef<string>(`session-${Date.now()}`);


  // 发送消息到后端
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

      // 调用后端 API（使用相对路径，通过 Vite 代理）
      const response = await axios.post('/api/chat', {
        query: userMessage,
        context_id: contextId.current,
      });

      const data = response.data;
      
      // 添加 AI 回复
      const aiMsg: Message = {
        key: messages.length + 1,
        role: 'ai',
        content: data.content || '抱歉，我没有收到有效的回复。',
      };
      setMessages(prev => [...prev, aiMsg]);
      
      message.success("消息发送成功！");
    } catch (error) {
      console.error('发送消息失败:', error);
      message.error("发送消息失败，请检查后端服务是否启动！");
      
      // 添加错误消息
      const errorMsg: Message = {
        key: messages.length + 1,
        role: 'ai',
        content: '抱歉，无法连接到服务器。请确保后端服务正在运行。',
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
        content="您好！我是 Moss AI 助手，很高兴为您服务。有什么可以帮助您的吗？"
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
            const userMessage = value;
            setValue("");
            message.info("正在发送消息...");
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
