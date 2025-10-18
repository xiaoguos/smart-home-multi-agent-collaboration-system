import type { MenuProps } from 'antd';
import { Layout, Menu } from 'antd';
import { Outlet } from 'react-router';
import React from 'react';
import './App.css';

const { Header, Content, Sider } = Layout;

const items1: MenuProps['items'] = [
  {
    key: '1',
    label: 'Home',
  },
  {
    key: '2',
    label: 'About',
  },
]

const items2: MenuProps['items'] = [
  {
    key: '1',
    label: '对话',
  },
  {
    key: '2',
    label: '关于',
  },
  {
    key: '3',
    label: '设置',
  },
]


const App: React.FC = () => (
  <Layout style={{ height: '100vh' }}>
    <Header className="header">
      <div className="logo" />
      <Menu theme="dark" mode="horizontal" defaultSelectedKeys={['2']} items={items1} />
    </Header>
    <Layout>
      <Sider width={200} className="site-layout-background">
        <Menu
          mode="inline"
          defaultSelectedKeys={['1']}
          defaultOpenKeys={['sub1']}
          style={{ height: '100%', borderRight: 0 }}
          items={items2}
        />
      </Sider>
      <Layout style={{ padding: '0 24px 24px' }}>
        <Content
          className="site-layout-background"
          style={{
            padding: 24,
            margin: 0,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  </Layout>
);

export default App;