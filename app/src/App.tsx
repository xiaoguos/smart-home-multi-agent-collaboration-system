import type { MenuProps } from 'antd';
import { Layout, Menu } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import React from 'react';
import './App.sass';
import Header from '@/components/Header.tsx';

const { Content, Sider } = Layout;

const sideBarMenus: MenuProps['items'] = [
  {
    key: 'chat',
    label: '对话',
  },
  {
    key: 'setting',
    label: '设置',
  },
  {
    key: 'about',
    label: '关于',
  },
]



const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // 处理侧边栏菜单点击
  const handleSideMenuClick = ({ key }: { key: string }) => {
    navigate(`/${key}`);
  };

/**
* 获取当前选中的导航键
*
* @returns 返回当前选中的导航键数组
*/
  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path === '/' || path === '/chat') return ['chat'];
    if (path === '/about') return ['about'];
    if (path === '/setting') return ['setting'];
    return ['chat'];
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Header />
      <Layout>
        <Sider width={200} className="site-layout-background">
          <Menu
            mode="inline"
            selectedKeys={getSelectedKeys()}
            style={{ height: '100%', borderRight: 0 }}
            items={sideBarMenus}
            onClick={handleSideMenuClick}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content
            className="site-layout-background"
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default App;