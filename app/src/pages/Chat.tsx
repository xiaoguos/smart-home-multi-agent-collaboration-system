import { Sender, Bubble } from "@ant-design/x";
import { RobotOutlined, UserOutlined, CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { App, Flex, Tag, Switch, Space } from "antd";
import React, { useState, useEffect } from "react";
import "./style/chat.sass";
import { sendMessageToConductor, testConductorConnection } from "../api/chat";
import { sendChatMessage, checkBackendHealth, checkChatHealth } from "../api/backend";

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
  const [useBackend, setUseBackend] = useState<boolean>(true); // 默认使用后端
  const { message } = App.useApp();
  const contextId = React.useRef<string>(`session-${Date.now()}`);

  // 检查服务连接状态
  useEffect(() => {
    const checkConnection = async () => {
      if (useBackend) {
        // 检查后端服务
        const backendOk = await checkBackendHealth();
        if (backendOk) {
          const chatOk = await checkChatHealth();
          setIsConnected(chatOk);
          if (!chatOk) {
            message.warning('后端服务正常，但无法连接到 Conductor Agent');
          }
        } else {
          setIsConnected(false);
          message.warning('无法连接到后端服务 (http://127.0.0.1:2100)');
        }
      } else {
        // 直连模式
        const connected = await testConductorConnection();
        setIsConnected(connected);
        if (!connected) {
          message.warning('无法连接到 Conductor Agent (http://localhost:12000)');
        }
      }
    };
    checkConnection();
  }, [message, useBackend]);

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

      let content: string;

      if (useBackend) {
        // 通过 FastAPI 后端发送
        const response = await sendChatMessage(userMessage, contextId.current);
        content = response.content;
        // 更新 context_id（如果后端返回了新的）
        if (response.context_id) {
          contextId.current = response.context_id;
        }
      } else {
        // 直连 Conductor Agent
        const aiResponse = await sendMessageToConductor(
          userMessage, 
          contextId.current
        );
        content = aiResponse.content;
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
      <div style={{ marginBottom: 16, textAlign: 'center' }}>
        <Space>
          <Switch 
            checked={useBackend} 
            onChange={setUseBackend}
            checkedChildren="后端模式"
            unCheckedChildren="直连模式"
          />
          <Tag 
            color={isConnected ? 'success' : 'error'} 
            icon={isConnected ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          >
            {isConnected 
              ? `✅ ${useBackend ? 'FastAPI 后端' : 'Conductor Agent'} 已连接` 
              : `❌ ${useBackend ? 'FastAPI 后端' : 'Conductor Agent'} 未连接`
            }
          </Tag>
        </Space>
      </div>
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
              message.error("Conductor Agent 未连接，请先启动服务！");
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
