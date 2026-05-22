import React, { useState, useEffect } from 'react';
import { Dropdown, Avatar, Space, message } from 'antd';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { getUserInfo, logout, clearUserInfo, type UserInfo } from '../api/auth';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  // 监听路由变化和localStorage变化来更新用户信息
  useEffect(() => {
    const updateUserInfo = () => {
      setUserInfo(getUserInfo());
    };
    
    updateUserInfo();
    
    // 监听storage事件（跨标签页）
    window.addEventListener('storage', updateUserInfo);
    
    // 监听自定义事件（同标签页）
    window.addEventListener('userInfoChanged', updateUserInfo);
    
    return () => {
      window.removeEventListener('storage', updateUserInfo);
      window.removeEventListener('userInfoChanged', updateUserInfo);
    };
  }, [location]);

  const handleLogout = async () => {
    try {
      await logout();
      clearUserInfo();
      message.success('退出登录成功');
      navigate('/welcome');
    } catch (error) {
      console.error('退出登录失败:', error);
      // 即使失败也清除本地信息
      clearUserInfo();
      navigate('/welcome');
    }
  };

  const menuItems = [
    {
      key: 'account-setting',
      icon: <SettingOutlined />,
      label: '账户设置',
      onClick: () => navigate('/account-setting'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <div className="header">
      <div className="header-left">欢迎使用智能管家系统</div>
      
      {userInfo && (
        <div className="header-right">
          <Dropdown menu={{ items: menuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} src={userInfo.avatar} />
              <span>{userInfo.nickname || userInfo.username}</span>
            </Space>
          </Dropdown>
        </div>
      )}
    </div>
  );
};

export default Header;
