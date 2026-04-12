import type { ReactNode } from "react";
import {
  CameraOutlined,
  CheckSquareOutlined,
  CloudOutlined,
  HomeOutlined,
  MessageOutlined,
  RocketOutlined,
  SoundOutlined,
} from "@ant-design/icons";

export type ConfigPluginKey =
  | "xiaomi"
  | "dida"
  | "wechat"
  | "openclaw"
  | "zeroclaw"
  | "camera"
  | "audio";

export interface ConfigPluginDefinition {
  key: ConfigPluginKey;
  title: string;
  blurb: string;
  icon: ReactNode;
}

// 插件菜单中的一级菜单由该注册表统一生成
export const ACCOUNT_SETTING_PLUGINS: ConfigPluginDefinition[] = [
  {
    key: "xiaomi",
    title: "小米账号",
    blurb: "智能家居与设备联动，语音与场景控制",
    icon: <HomeOutlined />,
  },
  {
    key: "dida",
    title: "滴答清单",
    blurb: "待办与任务同步，像清单插件一样接入助手",
    icon: <CheckSquareOutlined />,
  },
  {
    key: "wechat",
    title: "微信",
    blurb: "微信 MCP：聊天记录与消息发送（需网关下游已部署）",
    icon: <MessageOutlined />,
  },
  {
    key: "openclaw",
    title: "OpenClaw",
    blurb: "OpenClaw 页面嵌入侧边栏，与 ZeroClaw 分开配置",
    icon: <RocketOutlined />,
  },
  {
    key: "zeroclaw",
    title: "ZeroClaw",
    blurb: "ZeroClaw 页面嵌入侧边栏，与 OpenClaw 分开配置",
    icon: <CloudOutlined />,
  },
  {
    key: "camera",
    title: "摄像头插件",
    blurb: "支持本地摄像头与远程摄像头输入接入",
    icon: <CameraOutlined />,
  },
  {
    key: "audio",
    title: "音频 / ESP32",
    blurb: "在本页配置 stdio MCP（command/args）；启用后可在 Agent 中分配，模型提示优先走该 MCP",
    icon: <SoundOutlined />,
  },
];
