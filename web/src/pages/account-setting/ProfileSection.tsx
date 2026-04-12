import React, { useEffect, useState } from "react";
import { Card, Descriptions, Typography, Empty, Button, Form, Input, Space, message } from "antd";
import { UserOutlined, EditOutlined, SaveOutlined, CloseOutlined } from "@ant-design/icons";
import {
  getToken,
  saveUserInfo,
  updateUserProfile,
  type UserInfo,
} from "../../api/auth";

const { Text } = Typography;

export interface ProfileSectionProps {
  user: UserInfo | null;
}

const ProfileSection: React.FC<ProfileSectionProps> = ({ user }) => {
  const [form] = Form.useForm();
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(user);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setCurrentUser(user);
    if (user) {
      form.setFieldsValue({
        nickname: user.nickname ?? "",
        email: user.email ?? "",
        phone: user.phone ?? "",
        avatar: user.avatar ?? "",
      });
    }
  }, [form, user]);

  if (!currentUser) {
    return (
      <Card>
        <Empty description="未获取到用户信息，请重新登录" />
      </Card>
    );
  }

  const updateLocalUserInfo = (nextUser: UserInfo) => {
    const token = getToken();
    if (token) {
      saveUserInfo(token, nextUser);
      return;
    }
    localStorage.setItem("user_info", JSON.stringify(nextUser));
    window.dispatchEvent(new Event("userInfoChanged"));
  };

  const handleStartEdit = () => {
    form.setFieldsValue({
      nickname: currentUser.nickname ?? "",
      email: currentUser.email ?? "",
      phone: currentUser.phone ?? "",
      avatar: currentUser.avatar ?? "",
    });
    setEditing(true);
  };

  const handleCancelEdit = () => {
    setEditing(false);
    form.setFieldsValue({
      nickname: currentUser.nickname ?? "",
      email: currentUser.email ?? "",
      phone: currentUser.phone ?? "",
      avatar: currentUser.avatar ?? "",
    });
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const response = await updateUserProfile({
        user_id: currentUser.id,
        nickname: String(values.nickname ?? "").trim(),
        email: String(values.email ?? "").trim(),
        phone: String(values.phone ?? "").trim(),
        avatar: String(values.avatar ?? "").trim(),
      });
      setCurrentUser(response.user);
      updateLocalUserInfo(response.user);
      setEditing(false);
      message.success("基本信息已更新");
    } catch (error: unknown) {
      const formError = error as { errorFields?: unknown[] };
      if (Array.isArray(formError.errorFields)) {
        return;
      }
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      message.error(err.response?.data?.detail || err.message || "保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="用户基本信息" className="account-profile-card">
      <div className="account-profile-intro">
        <UserOutlined className="account-profile-icon" />
        <div>
          <Text strong style={{ fontSize: 16 }}>
            {currentUser.nickname || currentUser.username}
          </Text>
          <br />
          <Text type="secondary">@{currentUser.username}</Text>
        </div>
      </div>

      {!editing && (
        <>
          <Descriptions column={1} bordered size="small" style={{ marginTop: 16 }}>
            <Descriptions.Item label="用户 ID">{currentUser.id}</Descriptions.Item>
            <Descriptions.Item label="用户名">{currentUser.username}</Descriptions.Item>
            <Descriptions.Item label="昵称">{currentUser.nickname ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{currentUser.email ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="手机">{currentUser.phone ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="头像">{currentUser.avatar ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="注册时间">
              {currentUser.created_at ? new Date(currentUser.created_at).toLocaleString("zh-CN") : "—"}
            </Descriptions.Item>
          </Descriptions>
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={handleStartEdit}
            style={{ marginTop: 16 }}
          >
            编辑基本信息
          </Button>
        </>
      )}

      {editing && (
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="用户名">
            <Input value={currentUser.username} disabled />
          </Form.Item>
          <Form.Item
            name="nickname"
            label="昵称"
            rules={[
              { max: 50, message: "昵称最多 50 个字符" },
            ]}
          >
            <Input allowClear placeholder="请输入昵称" />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { type: "email", message: "请输入正确的邮箱地址" },
            ]}
          >
            <Input allowClear placeholder="请输入邮箱（可选）" />
          </Form.Item>
          <Form.Item
            name="phone"
            label="手机号"
            rules={[
              { pattern: /^[0-9+\-\s]*$/, message: "手机号仅支持数字、空格和 + -" },
            ]}
          >
            <Input allowClear placeholder="请输入手机号（可选）" />
          </Form.Item>
          <Form.Item
            name="avatar"
            label="头像地址"
            rules={[
              { type: "url", warningOnly: true, message: "建议输入合法 URL（可选）" },
            ]}
          >
            <Input allowClear placeholder="https://example.com/avatar.png（可选）" />
          </Form.Item>
          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => void handleSave()}
              loading={saving}
            >
              保存
            </Button>
            <Button icon={<CloseOutlined />} onClick={handleCancelEdit} disabled={saving}>
              取消
            </Button>
          </Space>
        </Form>
      )}
    </Card>
  );
};

export default ProfileSection;
