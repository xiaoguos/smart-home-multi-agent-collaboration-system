import React, { useState } from 'react';
import {
  Button,
  Typography,
  Space,
  Row,
  Col,
  Card,
  Form,
  Input,
  Tabs,
  message,
} from 'antd';
import {
  RobotOutlined,
  MessageOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  SafetyOutlined,
  HomeOutlined,
  ControlOutlined,
  CheckCircleOutlined,
  UserOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  login,
  register,
  saveUserInfo,
  isLoggedIn,
} from '@api/auth';
import type { UserInfo } from '@api/auth';
import './styles/index.sass';

const { Title, Paragraph } = Typography;

/** 开发环境跳过真实登录/注册接口，仅写入本地模拟会话 */
const isDevSkipAuth = import.meta.env.DEV;

function buildDevMockUser(partial: {
  username: string;
  nickname?: string;
}): UserInfo {
  return {
    id: 0,
    username: partial.username,
    nickname: partial.nickname ?? partial.username,
    created_at: new Date().toISOString(),
  };
}

const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);
  const [loginType, setLoginType] = useState<'password' | 'register'>(
    'password',
  );

  const handleStartChat = () => {
    if (isLoggedIn()) {
      navigate('/chat');
    } else {
      setShowLogin(true);
    }
  };

  const handleLogin = async (values: {
    username: string;
    password: string;
  }) => {
    if (isDevSkipAuth) {
      const user = buildDevMockUser({ username: values.username });
      saveUserInfo('dev-mock-token', user);
      message.success('开发环境：已跳过登录接口，进入对话');
      navigate('/chat');
      return;
    }

    try {
      const response = await login({
        username: values.username,
        password: values.password,
      });

      if (response.success && response.token && response.user) {
        message.success(response.message);
        saveUserInfo(response.token, response.user);

        if (!response.xiaomi_bound) {
          message.warning('您还未绑定小米账号，请先绑定');
          setTimeout(() => {
            navigate('/xiaomi-binding');
          }, 1500);
        } else {
          navigate('/chat');
        }
      } else {
        message.error(response.message || '登录失败');
      }
    } catch (error: unknown) {
      const msg
        = error instanceof Error ? error.message : '登录失败，请稍后重试';
      message.error(msg);
    }
  };

  const handleRegister = async (values: {
    username: string;
    password: string;
    email?: string;
    nickname?: string;
  }) => {
    if (isDevSkipAuth) {
      const user = buildDevMockUser({
        username: values.username,
        nickname: values.nickname,
      });
      saveUserInfo('dev-mock-token', user);
      message.success('开发环境：已跳过注册接口，进入对话');
      navigate('/chat');
      return;
    }

    try {
      const response = await register({
        username: values.username,
        password: values.password,
        email: values.email,
        nickname: values.nickname,
      });

      if (response.success && response.token && response.user) {
        message.success('注册成功！');
        saveUserInfo(response.token, response.user);
        message.info('请绑定小米账号以使用智能家居功能');
        setTimeout(() => {
          navigate('/xiaomi-binding');
        }, 1500);
      } else {
        message.error(response.message || '注册失败');
      }
    } catch (error: unknown) {
      const msg
        = error instanceof Error ? error.message : '注册失败，请稍后重试';
      message.error(msg);
    }
  };

  return (
    <div className="welcome-container">
      <div className={`welcome-content ${showLogin ? 'login-mode' : ''}`}>
        <Row gutter={[40, 40]} align="middle" justify="center">
          {!showLogin && (
            <Col xs={24} lg={8}>
              <div className="left-content">
                <Card className="feature-card">
                  <div className="card-header">
                    <BulbOutlined className="card-icon" />
                    <h3>智能特性</h3>
                  </div>
                  <div className="feature-list">
                    <div className="feature-point">
                      <CheckCircleOutlined className="check-icon" />
                      <span>自然语言理解</span>
                    </div>
                    <div className="feature-point">
                      <CheckCircleOutlined className="check-icon" />
                      <span>多轮对话记忆</span>
                    </div>
                    <div className="feature-point">
                      <CheckCircleOutlined className="check-icon" />
                      <span>实时学习优化</span>
                    </div>
                    <div className="feature-point">
                      <CheckCircleOutlined className="check-icon" />
                      <span>个性化推荐</span>
                    </div>
                  </div>
                </Card>
              </div>
            </Col>
          )}

          <Col
            xs={24}
            lg={showLogin ? 14 : 8}
            className={`main-content ${showLogin ? 'moved-left' : ''}`}
          >
            <Space
              direction="vertical"
              size="large"
              align="center"
              className="welcome-space"
            >
              <div className="welcome-icon">
                <RobotOutlined />
              </div>

              <div className="welcome-text">
                <Title level={1} className="welcome-title">
                  欢迎使用 Moss AI
                </Title>
                <Paragraph className="welcome-description">
                  您的智能AI助手，随时为您提供帮助和支持
                </Paragraph>
              </div>

              <div className="welcome-features">
                <Space size="large" wrap>
                  <div className="feature-item">
                    <MessageOutlined className="feature-icon" />
                    <span>智能对话</span>
                  </div>
                  <div className="feature-item">
                    <ThunderboltOutlined className="feature-icon" />
                    <span>快速响应</span>
                  </div>
                  <div className="feature-item">
                    <RobotOutlined className="feature-icon" />
                    <span>AI驱动</span>
                  </div>
                </Space>
              </div>
              {!showLogin && (
                <Button
                  type="primary"
                  size="large"
                  className="start-button"
                  onClick={handleStartChat}
                >
                  开始使用
                </Button>
              )}
            </Space>
          </Col>

          {!showLogin && (
            <Col xs={24} lg={8}>
              <div className="right-content">
                <Card className="advantages-card">
                  <div className="card-header">
                    <SafetyOutlined className="card-icon" />
                    <h3>核心优势</h3>
                  </div>
                  <div className="advantages-list">
                    <div className="advantage-point">
                      <HomeOutlined className="advantage-icon" />
                      <div className="advantage-content">
                        <div className="advantage-title">智能家居控制</div>
                        <div className="advantage-desc">
                          语音控制灯光、空调、窗帘等设备
                        </div>
                      </div>
                    </div>
                    <div className="advantage-point">
                      <SafetyOutlined className="advantage-icon" />
                      <div className="advantage-content">
                        <div className="advantage-title">安全可靠</div>
                        <div className="advantage-desc">
                          企业级安全保障，数据隐私保护
                        </div>
                      </div>
                    </div>
                    <div className="advantage-point">
                      <ControlOutlined className="advantage-icon" />
                      <div className="advantage-content">
                        <div className="advantage-title">场景联动</div>
                        <div className="advantage-desc">
                          智能场景设置，一键控制多个设备
                        </div>
                      </div>
                    </div>
                    <div className="advantage-point">
                      <ThunderboltOutlined className="advantage-icon" />
                      <div className="advantage-content">
                        <div className="advantage-title">极速响应</div>
                        <div className="advantage-desc">
                          毫秒级响应，流畅对话体验
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </Col>
          )}

          {showLogin && (
            <Col xs={24} lg={10} className="login-content">
              <div>
                <Card className="login-card">
                  <Title level={2} className="login-title">
                    用户登录
                  </Title>
                  <Tabs
                    activeKey={loginType}
                    onChange={(key) =>
                      setLoginType(key as 'password' | 'register')
                    }
                    centered
                    className="login-tabs"
                    items={[
                      {
                        key: 'password',
                        label: (
                          <span>
                            <UserOutlined />
                            密码登录
                          </span>
                        ),
                        children: (
                          <Form
                            name="login"
                            onFinish={handleLogin}
                            layout="vertical"
                            className="login-form"
                          >
                            <Form.Item
                              name="username"
                              label="用户名"
                              rules={[
                                { required: true, message: '请输入用户名!' },
                              ]}
                            >
                              <Input
                                prefix={<UserOutlined />}
                                placeholder="默认账号: admin"
                                size="large"
                              />
                            </Form.Item>
                            <Form.Item
                              name="password"
                              label="密码"
                              rules={[
                                { required: true, message: '请输入密码!' },
                              ]}
                            >
                              <Input.Password
                                prefix={<LockOutlined />}
                                placeholder="admin123"
                                size="large"
                              />
                            </Form.Item>
                            <Form.Item>
                              <Button
                                type="primary"
                                htmlType="submit"
                                size="large"
                                className="login-button"
                                block
                              >
                                登录
                              </Button>
                            </Form.Item>
                            <div
                              style={{ textAlign: 'center', marginTop: 16 }}
                            >
                              <Button
                                type="link"
                                onClick={() => setLoginType('register')}
                              >
                                还没有账号？立即注册
                              </Button>
                            </div>
                          </Form>
                        ),
                      },
                      {
                        key: 'register',
                        label: (
                          <span>
                            <UserOutlined />
                            注册账号
                          </span>
                        ),
                        children: (
                          <Form
                            name="register"
                            onFinish={handleRegister}
                            layout="vertical"
                            className="login-form"
                          >
                            <Form.Item
                              name="username"
                              label="用户名"
                              rules={[
                                { required: true, message: '请输入用户名!' },
                                { min: 3, message: '用户名至少3个字符!' },
                              ]}
                            >
                              <Input
                                prefix={<UserOutlined />}
                                placeholder="请输入用户名（3-50字符）"
                                size="large"
                              />
                            </Form.Item>
                            <Form.Item
                              name="password"
                              label="密码"
                              rules={[
                                { required: true, message: '请输入密码!' },
                                { min: 6, message: '密码至少6个字符!' },
                              ]}
                            >
                              <Input.Password
                                prefix={<LockOutlined />}
                                placeholder="请输入密码（至少6个字符）"
                                size="large"
                              />
                            </Form.Item>
                            <Form.Item name="nickname" label="昵称（可选）">
                              <Input placeholder="请输入昵称" size="large" />
                            </Form.Item>
                            <Form.Item>
                              <Button
                                type="primary"
                                htmlType="submit"
                                size="large"
                                className="login-button"
                                block
                              >
                                注册
                              </Button>
                            </Form.Item>
                            <div
                              style={{ textAlign: 'center', marginTop: 16 }}
                            >
                              <Button
                                type="link"
                                onClick={() => setLoginType('password')}
                              >
                                已有账号？立即登录
                              </Button>
                            </div>
                          </Form>
                        ),
                      },
                    ]}
                  />
                </Card>
              </div>
            </Col>
          )}
        </Row>
      </div>
    </div>
  );
};

export default Welcome;
