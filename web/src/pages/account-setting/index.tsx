import React from "react";
import { Typography } from "antd";
import Header from "../../components/Header";
import { getUserInfo } from "../../api/auth";
import ProfileSection from "./ProfileSection";
import "./account-setting.sass";

const { Title } = Typography;

const AccountSetting: React.FC = () => {
  const userInfo = getUserInfo();

  return (
    <div className="account-setting-page">
      <Header />
      <div className="account-setting-container">
        <div className="setting-content">
          <Title level={2} className="account-setting-main-title">
            账户设置
          </Title>
          <ProfileSection user={userInfo} />
        </div>
      </div>
    </div>
  );
};

export default AccountSetting;
