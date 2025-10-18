import { Sender, Bubble } from "@ant-design/x";
import { RobotOutlined } from "@ant-design/icons";
import { App, Flex } from "antd";
import React, { useState } from "react";
import "./style/chat.sass";

const userAvatar: React.CSSProperties = {
  color: "#1890ff",
  backgroundColor: "#e6f7ff",
};

const Chat: React.FC = () => {
  const [value, setValue] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const { message } = App.useApp();

  React.useEffect(() => {
    if (loading) {
      const timer = setTimeout(() => {
        setLoading(false);
        message.success("消息发送成功！");
      }, 2000);
      return () => {
        clearTimeout(timer);
      };
    }
  }, [loading]);

  return (
    <div className="chat-container">
      <Bubble
        placement="start"
        content="您好！我是 Moss AI 助手，很高兴为您服务。有什么可以帮助您的吗？"
        avatar={{
          icon: <RobotOutlined />,
          style: userAvatar,
        }}
      />
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
            setValue("");
            setLoading(true);
            message.info("正在发送消息...");
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
