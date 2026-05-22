import React, { useEffect, useMemo, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { Layout, Menu } from "antd";
import Header from "@/components/Header.tsx";
import { useClawSettings } from "@/hooks/useClawSettings";

const { Content, Sider } = Layout;

export const RootLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [openKeys, setOpenKeys] = useState<string[]>([]);
  const claw = useClawSettings();

  const sideBarMenus: MenuProps["items"] = useMemo(() => {
    const core: NonNullable<MenuProps["items"]> = [
      { key: "chat", label: "对话" },
      { key: "model-config", label: "模型配置" },
      { key: "agent-config", label: "Agent配置" },
      { key: "plugin-config", label: "插件菜单" },
      { key: "knowledge", label: "知识库" },
      {
        key: "devices",
        label: "设备",
        children: [
          { key: "devices-local", label: "自定义设备" },
          { key: "devices-mihome", label: "米家设备" },
        ],
      },
    ];
    const tail: NonNullable<MenuProps["items"]> = [{ key: "about", label: "关于" }];
    if (claw.hasAny) {
      const children: NonNullable<MenuProps["items"]> = [];
      if (claw.hasOpen) children.push({ key: "claw-open", label: "OpenClaw" });
      if (claw.hasZero) children.push({ key: "claw-zero", label: "ZeroClaw" });
      return [...core, { key: "claw", label: "Claw", children }, ...tail];
    }
    return [...core, ...tail];
  }, [claw.hasAny, claw.hasOpen, claw.hasZero]);

  useEffect(() => {
    const p = location.pathname;
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (p.startsWith("/devices")) next.add("devices");
      if (p.startsWith("/claw")) next.add("claw");
      return [...next];
    });
  }, [location.pathname]);

  const handleSideMenuClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "chat") navigate("/chat");
    else if (key === "about") navigate("/about");
    else if (key === "model-config") navigate("/models");
    else if (key === "agent-config") navigate("/agents");
    else if (key === "plugin-config") navigate("/plugins");
    else if (key === "knowledge") navigate("/knowledge");
    else if (key === "devices-local") navigate("/devices/local");
    else if (key === "devices-mihome") navigate("/devices/mihome");
    else if (key === "claw-open") navigate("/claw/open");
    else if (key === "claw-zero") navigate("/claw/zero");
  };

  const getSelectedKeys = (): string[] => {
    const path = location.pathname;
    if (path === "/" || path === "/chat") return ["chat"];
    if (path === "/about") return ["about"];
    if (path.startsWith("/models")) return ["model-config"];
    if (path.startsWith("/agents")) return ["agent-config"];
    if (path.startsWith("/plugins")) return ["plugin-config"];
    if (path.startsWith("/knowledge")) return ["knowledge"];
    if (path.startsWith("/devices/local")) return ["devices-local"];
    if (path.startsWith("/devices/mihome")) return ["devices-mihome"];
    if (path.startsWith("/claw/open")) return ["claw-open"];
    if (path.startsWith("/claw/zero")) return ["claw-zero"];
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
