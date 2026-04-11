import React from "react";
import { Card, Descriptions, Typography, Empty } from "antd";
import { UserOutlined } from "@ant-design/icons";
import type { UserInfo } from "../../api/auth";

const { Text } = Typography;

export interface ProfileSectionProps {
  user: UserInfo | null;
}

const ProfileSection: React.FC<ProfileSectionProps> = ({ user }) => {
  if (!user) {
    return (
      <Card>
        <Empty description="未获取到用户信息，请重新登录" />
      </Card>
    );
  }

  return (
    <Card title="用户基本信息" className="account-profile-card">
      <div className="account-profile-intro">
        <UserOutlined className="account-profile-icon" />
        <div>
          <Text strong style={{ fontSize: 16 }}>
            {user.nickname || user.username}
          </Text>
          <br />
          <Text type="secondary">@{user.username}</Text>
        </div>
      </div>
      <Descriptions column={1} bordered size="small" style={{ marginTop: 16 }}>
        <Descriptions.Item label="用户 ID">{user.id}</Descriptions.Item>
        <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
        <Descriptions.Item label="昵称">{user.nickname ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="邮箱">{user.email ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="手机">{user.phone ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="注册时间">
          {user.created_at ? new Date(user.created_at).toLocaleString("zh-CN") : "—"}
        </Descriptions.Item>
      </Descriptions>
      <Text type="secondary" style={{ display: "block", marginTop: 16, fontSize: 12 }}>
        说明：昵称、邮箱等修改需后端支持用户资料更新接口后在此开放编辑。
      </Text>
    </Card>
  );
};

export default ProfileSection;
