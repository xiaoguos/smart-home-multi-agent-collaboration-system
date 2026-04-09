import React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { Layout, Menu } from "antd";
import Header from "@/components/Header.tsx";

const { Content, Sider } = Layout;

const sideBarMenus: MenuProps["items"] = [
  {
    key: "chat",
    label: "对话",
  },
  {
    key: "setting",
    label: "设置",
  },
  {
    key: "about",
    label: "关于",
  },
];


export const RootLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleSideMenuClick: MenuProps["onClick"] = ({ key }) => {
    navigate(`/${key}`);
  };


  const getSelectedKeys = (): string[] => {
    const path = location.pathname;
    if (path === "/" || path === "/chat") return ["chat"];
    if (path === "/about") return ["about"];
    if (path === "/setting") return ["setting"];
    return ["chat"];
  };

  return (
    <div className="app">
      <Header />
      <Layout className="app-content">
        <Sider width={200} className="site-layout-background">
          <Menu
            mode="inline"
            selectedKeys={getSelectedKeys()}
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
