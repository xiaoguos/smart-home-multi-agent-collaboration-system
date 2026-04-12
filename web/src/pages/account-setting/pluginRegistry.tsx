import type { ReactNode } from "react";
import {
  CheckSquareOutlined,
  CloudOutlined,
  HomeOutlined,
  RocketOutlined,
} from "@ant-design/icons";

export type ConfigPluginKey = "xiaomi" | "dida" | "openclaw" | "zeroclaw";

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
];
