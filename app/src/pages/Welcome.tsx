import React, { useState, useEffect } from "react";
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
  QRCode,
  Spin,
  message,
} from "antd";
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
  WechatOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { WECHAT_CONFIG, generateWechatLoginUrl, generateSceneId } from "@/config/wechat";
import { login, register, saveUserInfo, isLoggedIn } from "../api/auth";
import "./style/welcome.sass";

const { Title, Paragraph } = Typography;

const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);
  const [loginType, setLoginType] = useState("password");
  const [qrCodeUrl, setQrCodeUrl] = useState("");
  const [qrCodeStatus, setQrCodeStatus] = useState<
    "loading" | "ready" | "scanned" | "expired"
  >("loading");
  const [pollingInterval, setPollingInterval] = useState<number | null>(null);

  const handleStartChat = () => {
    // 检查是否已登录
    if (isLoggedIn()) {
      navigate("/chat");
    } else {
      setShowLogin(true);
    }
  };

  const handleLogin = async (values: any) => {
    try {
      const response = await login({
        username: values.username,
        password: values.password,
      });

      if (response.success && response.token && response.user) {
        message.success(response.message);
        // 保存用户信息
        saveUserInfo(response.token, response.user);
        
        // 检查是否绑定小米账号
        if (!response.xiaomi_bound) {
          message.warning("您还未绑定小米账号，请先绑定");
          setTimeout(() => {
            navigate("/xiaomi-binding");
          }, 1500);
        } else {
          navigate("/chat");
        }
      } else {
        message.error(response.message || "登录失败");
      }
    } catch (error: any) {
      console.error("登录失败:", error);
      message.error(error.message || "登录失败，请稍后重试");
    }
  };

  // 处理注册
  const handleRegister = async (values: any) => {
    try {
      const response = await register({
        username: values.username,
        password: values.password,
        email: values.email,
        nickname: values.nickname,
      });

      if (response.success && response.token && response.user) {
        message.success("注册成功！");
        // 保存用户信息
        saveUserInfo(response.token, response.user);
        // 注册后需要绑定小米账号
        message.info("请绑定小米账号以使用智能家居功能");
        setTimeout(() => {
          navigate("/xiaomi-binding");
        }, 1500);
      } else {
        message.error(response.message || "注册失败");
      }
    } catch (error: any) {
      console.error("注册失败:", error);
      message.error(error.message || "注册失败，请稍后重试");
    }
  };

  // 生成微信二维码
  const generateWechatQR = async () => {
    setQrCodeStatus("loading");
    try {
      // 生成随机场景ID
      const sceneId = generateSceneId();
      
      // 生成微信登录URL
      const wechatLoginUrl = generateWechatLoginUrl(sceneId);
      
      setQrCodeUrl(wechatLoginUrl);
      setQrCodeStatus("ready");
      
      // 开始轮询二维码状态（检查用户是否扫描）
      startQRCodePolling(sceneId);
    } catch (error) {
      console.error("生成二维码失败:", error);
      message.error("生成二维码失败，请重试");
      setQrCodeStatus("expired");
    }
  };

  // 轮询二维码状态
  const startQRCodePolling = (sceneId: string) => {
    const interval = setInterval(async () => {
      try {
        // 检查本地存储中是否有微信登录成功的信息
        const wechatLoginData = localStorage.getItem(`wechat_login_${sceneId}`);
        
        if (wechatLoginData) {
          const loginInfo = JSON.parse(wechatLoginData);
          
          if (loginInfo.status === 'scanned') {
            setQrCodeStatus("scanned");
            message.success("二维码已扫描，请确认登录");
          } else if (loginInfo.status === 'success') {
            clearInterval(interval);
            setPollingInterval(null);
            
            // 调用后端API进行登录
            const loginResult = await handleWechatLogin(loginInfo);
            if (loginResult.success) {
              message.success("登录成功！");
              navigate("/chat");
            } else {
              message.error("登录失败，请重试");
              setQrCodeStatus("expired");
            }
            
            // 清理本地存储
            localStorage.removeItem(`wechat_login_${sceneId}`);
          }
        }
        
        // 检查是否超时
        const startTime = parseInt(sceneId.split('_')[1]);
        if (Date.now() - startTime > WECHAT_CONFIG.QR_CODE_EXPIRE_TIME) {
          clearInterval(interval);
          setPollingInterval(null);
          setQrCodeStatus("expired");
          message.warning("二维码已过期，请重新生成");
        }
      } catch (error) {
        console.error("检查二维码状态失败:", error);
      }
    }, WECHAT_CONFIG.POLLING_INTERVAL);

    setPollingInterval(interval as unknown as number | null);
  };

  // 处理微信登录
  const handleWechatLogin = async (loginInfo: any) => {
    try {
      const response = await fetch('/api/auth/wechat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: loginInfo.code,
          state: loginInfo.state,
          openid: loginInfo.openid,
          unionid: loginInfo.unionid,
          nickname: loginInfo.nickname,
          avatar: loginInfo.avatar
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 保存用户信息到本地存储
        localStorage.setItem('user_token', result.token);
        localStorage.setItem('user_info', JSON.stringify(result.user));
        return { success: true };
      } else {
        return { success: false, error: result.message };
      }
    } catch (error) {
      console.error('微信登录失败:', error);
      return { success: false, error: '网络错误' };
    }
  };

  // 刷新二维码
  const refreshQRCode = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
    generateWechatQR();
  };

  // 组件挂载时生成二维码
  useEffect(() => {
    if (showLogin && loginType === "wechat") {
      generateWechatQR();
    }

    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [showLogin, loginType]);

  // 切换登录方式时重新生成二维码
  useEffect(() => {
    if (loginType === "wechat" && showLogin) {
      generateWechatQR();
    }
  }, [loginType]);

  return (
    <div className="welcome-container">
      <div className={`welcome-content ${showLogin ? "login-mode" : ""}`}>
        <Row gutter={[40, 40]} align="middle" justify="center">
          {/* 左侧内容 - 条件渲染 */}
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

          {/* 中间主要内容 - 动画移动到左边 */}
          <Col
            xs={24}
            lg={showLogin ? 14 : 8}
            className={`main-content ${showLogin ? "moved-left" : ""}`}
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

          {/* 右侧内容 - 条件渲染 */}
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

          {/* 登录框 - 显示在右侧 */}
          {showLogin && (
            <Col xs={24} lg={10} className="login-content">
              <div>
                <Card className="login-card">
                  <Title level={2} className="login-title">
                    用户登录
                  </Title>
                  <Tabs
                    activeKey={loginType}
                    onChange={setLoginType}
                    centered
                    className="login-tabs"
                    items={[
                      {
                        key: "password",
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
                                { required: true, message: "请输入用户名!" },
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
                                { required: true, message: "请输入密码!" },
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
                            <div style={{ textAlign: 'center', marginTop: 16 }}>
                              <Button type="link" onClick={() => setLoginType("register")}>
                                还没有账号？立即注册
                              </Button>
                            </div>
                          </Form>
                        ),
                      },
                      {
                        key: "register",
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
                                { required: true, message: "请输入用户名!" },
                                { min: 3, message: "用户名至少3个字符!" },
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
                                { required: true, message: "请输入密码!" },
                                { min: 6, message: "密码至少6个字符!" },
                              ]}
                            >
                              <Input.Password
                                prefix={<LockOutlined />}
                                placeholder="请输入密码（至少6个字符）"
                                size="large"
                              />
                            </Form.Item>
                            <Form.Item
                              name="nickname"
                              label="昵称（可选）"
                            >
                              <Input
                                placeholder="请输入昵称"
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
                                注册
                              </Button>
                            </Form.Item>
                            <div style={{ textAlign: 'center', marginTop: 16 }}>
                              <Button type="link" onClick={() => setLoginType("password")}>
                                已有账号？立即登录
                              </Button>
                            </div>
                          </Form>
                        ),
                      },
                      {
                        key: "wechat",
                        label: (
                          <span>
                            <WechatOutlined />
                            微信登录
                          </span>
                        ),
                        children: (
                          <div className="wechat-login">
                            <div className="qr-code-container">
                              {qrCodeStatus === "loading" && (
                                <div className="qr-loading">
                                  <Spin size="large" />
                                  <p>正在生成二维码...</p>
                                </div>
                              )}

                              {qrCodeStatus === "ready" && (
                                <div className="qr-ready">
                                  <QRCode
                                    value={qrCodeUrl || "https://example.com"}
                                    size={200}
                                    status="active"
                                    className="qr-code"
                                  />
                                  <p className="qr-tip">
                                    请使用微信扫描二维码登录
                                  </p>
                                  <Button
                                    type="link"
                                    icon={<ReloadOutlined />}
                                    onClick={refreshQRCode}
                                    className="refresh-btn"
                                  >
                                    刷新二维码
                                  </Button>
                                </div>
                              )}

                              {qrCodeStatus === "scanned" && (
                                <div className="qr-scanned">
                                  <QRCode
                                    value={qrCodeUrl || "https://example.com"}
                                    size={200}
                                    status="active"
                                    className="qr-code"
                                  />
                                  <p className="qr-tip success">
                                    二维码已扫描，请在手机上确认登录
                                  </p>
                                  <Button
                                    type="link"
                                    icon={<ReloadOutlined />}
                                    onClick={refreshQRCode}
                                    className="refresh-btn"
                                  >
                                    重新生成
                                  </Button>
                                </div>
                              )}

                              {qrCodeStatus === "expired" && (
                                <div className="qr-expired">
                                  <div className="qr-placeholder">
                                    <WechatOutlined className="expired-icon" />
                                  </div>
                                  <p className="qr-tip error">二维码已过期</p>
                                  <Button
                                    type="primary"
                                    icon={<ReloadOutlined />}
                                    onClick={refreshQRCode}
                                    className="refresh-btn"
                                  >
                                    重新生成二维码
                                  </Button>
                                </div>
                              )}
                            </div>

                            <div className="wechat-tips">
                              <p>• 使用微信扫描上方二维码</p>
                              <p>• 在手机上确认登录即可完成登录</p>
                              <p>• 首次使用将自动注册账号</p>
                            </div>
                          </div>
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
