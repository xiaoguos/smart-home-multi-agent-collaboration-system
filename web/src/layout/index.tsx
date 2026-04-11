import React, { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { Layout, Menu } from "antd";
import Header from "@/components/Header.tsx";

const { Content, Sider } = Layout;

const sideBarMenus: MenuProps["items"] = [
  { key: "chat", label: "对话" },
  {
    key: "models",
    label: "模型",
    children: [{ key: "models-llm", label: "LLM 模型" }],
  },
  {
    key: "agents",
    label: "Agent",
    children: [
      { key: "agents-conn", label: "连接与状态" },
      { key: "agents-prompt", label: "系统提示词" },
    ],
  },
  {
    key: "devices",
    label: "设备",
    children: [
      { key: "devices-local", label: "本地设备" },
      { key: "devices-mihome", label: "米家设备" },
    ],
  },
  { key: "about", label: "关于" },
];

export const RootLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [openKeys, setOpenKeys] = useState<string[]>([]);

  useEffect(() => {
    const p = location.pathname;
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (p.startsWith("/models")) next.add("models");
      if (p.startsWith("/agents")) next.add("agents");
      if (p.startsWith("/devices")) next.add("devices");
      return [...next];
    });
  }, [location.pathname]);

  const handleSideMenuClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "chat") navigate("/chat");
    else if (key === "about") navigate("/about");
    else if (key === "models-llm") navigate("/models/llm");
    else if (key === "agents-conn") navigate("/agents/connections");
    else if (key === "agents-prompt") navigate("/agents/prompts");
    else if (key === "devices-local") navigate("/devices/local");
    else if (key === "devices-mihome") navigate("/devices/mihome");
  };

  const getSelectedKeys = (): string[] => {
    const path = location.pathname;
    if (path === "/" || path === "/chat") return ["chat"];
    if (path === "/about") return ["about"];
    if (path.startsWith("/models/llm")) return ["models-llm"];
    if (path.startsWith("/agents/connections")) return ["agents-conn"];
    if (path.startsWith("/agents/prompts")) return ["agents-prompt"];
    if (path.startsWith("/devices/local")) return ["devices-local"];
    if (path.startsWith("/devices/mihome")) return ["devices-mihome"];
    return ["chat"];
  };

  return (
    <div className="app">
      <Header />
      <Layout className="app-content">
        <Sider width={220} className="site-layout-background">
          <Menu
            mode="inline"
            selectedKeys={getSelectedKeys()}
            openKeys={openKeys}
            onOpenChange={setOpenKeys}
            style={{ height: "100%", borderRight: 0 }}
            items={sideBarMenus}
            onClick={handleSideMenuClick}
          />
        </Sider>
        <Layout>
          <Content className="site-layout-background">
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </div>
  );
};
