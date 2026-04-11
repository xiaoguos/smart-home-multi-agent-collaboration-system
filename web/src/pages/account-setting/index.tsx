import React, { useState } from "react";
import { Tabs, Typography } from "antd";
import { UserOutlined, LinkOutlined } from "@ant-design/icons";
import Header from "../../components/Header";
import { getUserInfo } from "../../api/auth";
import ProfileSection from "./ProfileSection";
import BindingSection from "./BindingSection";
import "./account-setting.sass";

const { Title } = Typography;

const AccountSetting: React.FC = () => {
  const [tab, setTab] = useState<string>("profile");
  const userInfo = getUserInfo();

  const tabItems = [
    {
      key: "profile",
      label: (
        <span>
          <UserOutlined />
          基本信息
        </span>
      ),
      children: <ProfileSection user={userInfo} />,
    },
    {
      key: "bindings",
      label: (
        <span>
          <LinkOutlined />
          配置清单
        </span>
      ),
      children: <BindingSection userInfo={userInfo} />,
    },
  ];

  return (
    <div className="account-setting-page">
      <Header />
      <div className="account-setting-container">
        <div className="setting-content">
          <Title level={2} className="account-setting-main-title">
            账户设置
          </Title>
          <Tabs
            activeKey={tab}
            items={tabItems}
            onChange={setTab}
            size="large"
            className="account-setting-tabs"
          />
        </div>
      </div>
    </div>
  );
};

export default AccountSetting;
