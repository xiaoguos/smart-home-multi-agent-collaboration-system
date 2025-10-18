import { Sender, Bubble, type BubbleProps } from "@ant-design/x";
import { RobotOutlined, UserOutlined } from "@ant-design/icons";
import { App, Flex, type GetProp, type GetRef } from "antd";
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

  const text = "Ant Design X love you! ";

  const correctionExamples = [
    "The weather is nice today.",
    "The weather is bad today.",
    "The weather is very nice today.",
    "Tomorrow the weather will be better.",
  ];

  

  const rolesAsFunction = (bubbleData: BubbleProps, index: number) => {
    const RenderIndex: BubbleProps['messageRender'] = (content) => (
      <Flex>
        #{index}: {content}
      </Flex>
    );
    switch (bubbleData.role) {
      case 'ai':
        return {
          placement: 'start' as const,
          avatar: { icon: <UserOutlined />, style: { background: '#fde3cf' } },
          typing: { step: 5, interval: 20 },
          style: {
            maxWidth: 600,
          },
          messageRender: RenderIndex,
        };
      case 'user':
        return {
          placement: 'end' as const,
          avatar: { icon: <UserOutlined />, style: { background: '#87d068' } },
          messageRender: RenderIndex,
        };
      default:
        return { messageRender: RenderIndex };
    }
  };
  
  const rolesAsObject: GetProp<typeof Bubble.List, 'roles'> = {
    ai: {
      placement: 'start',
      avatar: { icon: <UserOutlined />, style: { background: '#fde3cf' } },
      typing: { step: 5, interval: 20 },
      style: {
        maxWidth: 600,
      },
    },
    user: {
      placement: 'end',
      avatar: { icon: <UserOutlined />, style: { background: '#87d068' } },
    },
  };
  

  const [repeat, setRepeat] = React.useState(1);
  const [correctionDemo, setCorrectionDemo] = React.useState(0);
  const [count, setCount] = React.useState(3);
  const [useRolesAsFunction, setUseRolesAsFunction] = React.useState(false);
  const listRef = React.useRef<GetRef<typeof Bubble.List>>(null);
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
          <Bubble.List
        ref={listRef}
        style={{ maxHeight: 300, paddingInline: 16 }}
        roles={useRolesAsFunction ? rolesAsFunction : rolesAsObject}
        items={Array.from({ length: count }).map((_, i) => {
          const isAI = !!(i % 2);
          const content = isAI ? 'Mock AI content. '.repeat(20) : 'Mock user content.';

          return { key: i, role: isAI ? 'ai' : 'user', content };
        })}
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
