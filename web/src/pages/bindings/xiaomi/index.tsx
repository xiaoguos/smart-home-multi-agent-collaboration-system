import React, { useState, useEffect } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  Steps,
  message,
  Alert,
  Image,
  Typography,
  Space,
} from "antd";
import {
  UserOutlined,
  LockOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import {
  startXiaomiLogin,
  submitCaptcha,
  verify2FA,
  resend2FACode,
  getCaptchaUrl,
  manualBindCredentials,
} from "../../../api/xiaomi";
import "../styles/xiaomi-binding.sass";

const { Title, Text, Paragraph } = Typography;

const XiaomiBinding: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [captchaForm] = Form.useForm();
  const [twoFAForm] = Form.useForm();
  const [manualForm] = Form.useForm();

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [captchaUrl, setCaptchaUrl] = useState<string>("");
  const [verifyMethod, setVerifyMethod] = useState<string>("手机或邮箱");
  const [resendingCode, setResendingCode] = useState(false);
  const [autoResendAttempted, setAutoResendAttempted] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [verifyUrl, setVerifyUrl] = useState<string>("");
  const [showManualInput, setShowManualInput] = useState(false);
  const [xiaomiUsername, setXiaomiUsername] = useState<string>("");

  /**
   * 步骤1：提交账号密码
   */
  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      // 从 localStorage 获取用户信息
      const userStr = localStorage.getItem('user_info');
      if (!userStr) {
        message.error('请先登录系统账号');
        navigate('/');
        return;
      }
      
      const user = JSON.parse(userStr);
      setXiaomiUsername(values.username); // 保存小米账号用于手动输入
      
      const response = await startXiaomiLogin({
        system_user_id: user.id,
        username: values.username,
        password: values.password,
        server: "cn",
      });

      setSessionId(response.session_id);

      if (response.status === "need_captcha") {
        // 需要验证码
        message.info(response.message);
        setCaptchaUrl(getCaptchaUrl(response.session_id));
        setCurrentStep(1);
      } else if (response.status === "need_2fa") {
        // 需要双因素认证
        message.success(response.message);
        setVerifyMethod(response.data?.verify_method || "手机或邮箱");
        setVerifyUrl(response.data?.verify_url || ""); // 保存验证URL
        setAutoResendAttempted(true); // 后端已自动发送，标记为已尝试
        setCurrentStep(2);
      } else if (response.status === "success") {
        // 绑定成功
        message.success(response.message);
        setCurrentStep(3);
        setTimeout(() => {
          navigate("/chat");
        }, 2000);
      } else {
        message.error(response.message || "绑定失败");
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || "绑定账号失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  /**
   * 步骤2：提交验证码
   */
  const handleCaptchaSubmit = async (values: { captcha_code: string }) => {
    setLoading(true);
    try {
      const response = await submitCaptcha({
        session_id: sessionId,
        captcha_code: values.captcha_code,
      });

      if (response.status === "need_captcha") {
        // 验证码错误，刷新验证码
        message.error(response.message);
        setCaptchaUrl(getCaptchaUrl(response.session_id) + "?t=" + Date.now());
        captchaForm.resetFields();
      } else if (response.status === "need_2fa") {
        // 需要双因素认证
        message.success(response.message);
        setVerifyMethod(response.data?.verify_method || "手机或邮箱");
        setVerifyUrl(response.data?.verify_url || ""); // 保存验证URL
        setAutoResendAttempted(true); // 后端已自动发送，标记为已尝试
        setCurrentStep(2);
      } else if (response.status === "success") {
        // 绑定成功
        message.success(response.message);
        setCurrentStep(3);
        setTimeout(() => {
          navigate("/chat");
        }, 2000);
      } else {
        message.error(response.message || "验证码验证失败");
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || "验证码提交失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  /**
   * 步骤3：提交双因素认证码
   */
  const handle2FASubmit = async (values: { ticket: string }) => {
    setLoading(true);
    try {
      const response = await verify2FA({
        session_id: sessionId,
        ticket: values.ticket,
      });

      if (response.status === "success") {
        message.success(response.message);
        setCurrentStep(3);
        setTimeout(() => {
          navigate("/chat");
        }, 2000);
      } else {
        message.error(response.message || "双因素认证失败");
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || "双因素认证失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  /**
   * 刷新验证码
   */
  const refreshCaptcha = () => {
    setCaptchaUrl(getCaptchaUrl(sessionId) + "?t=" + Date.now());
  };

  /**
   * 重新发送双因素认证验证码
   */
  const handleResend2FACode = async (silent: boolean = false) => {
    setResendingCode(true);
    try {
      const response = await resend2FACode(sessionId);
      if (response.status === "need_2fa") {
        if (!silent) {
          message.success(response.message);
        }
        setVerifyMethod(response.data?.verify_method || "手机或邮箱");
        // 发送成功后开始180秒倒计时
        setCountdown(180);
      } else {
        if (!silent) {
          message.error(response.message || "发送失败");
        }
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || "发送失败，请重试";
      
      // 检查是否是429错误（发送过于频繁）
      if (error.response?.status === 429) {
        // 尝试从错误信息中提取剩余秒数
        const match = errorMsg.match(/请(\d+)秒后再试/);
        if (match) {
          const remainingSeconds = parseInt(match[1]);
          setCountdown(remainingSeconds);
        }
      }
      
      if (!silent) {
        message.error(errorMsg);
      }
    } finally {
      setResendingCode(false);
    }
  };

  /**
   * 当进入2FA步骤且验证码未自动发送时，自动重新发送
   */
  useEffect(() => {
    if (currentStep === 2 && !autoResendAttempted && verifyMethod === "手机或邮箱") {
      setAutoResendAttempted(true);
      handleResend2FACode(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  /**
   * 倒计时效果
   */
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  /**
   * 进入2FA步骤时启动倒计时
   */
  useEffect(() => {
    if (currentStep === 2) {
      setCountdown(180);
    }
  }, [currentStep]);

  /**
   * 手动输入凭证
   */
  const handleManualBind = async (values: any) => {
    setLoading(true);
    try {
      // 从 localStorage 获取用户信息
      const userStr = localStorage.getItem('user_info');
      if (!userStr) {
        message.error('请先登录系统账号');
        navigate('/');
        return;
      }
      
      const user = JSON.parse(userStr);
      
      const response = await manualBindCredentials({
        system_user_id: user.id,
        xiaomi_username: xiaomiUsername || values.xiaomi_username,
        ssecurity: values.ssecurity.trim(),
        userId: values.userId.trim(),
        cUserId: values.cUserId.trim(),
        serviceToken: values.serviceToken.trim(),
        server: "cn",
      });

      if (response.status === "success") {
        message.success(response.message);
        setCurrentStep(3);
        setTimeout(() => {
          navigate("/chat");
        }, 2000);
      } else {
        message.error(response.message || "绑定失败");
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || "绑定失败，请检查参数是否正确");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="xiaomi-binding-container">
      <Card className="binding-card">
        <Title level={2} style={{ textAlign: "center", marginBottom: 30 }}>
          绑定小米账号
        </Title>

        <Steps
          current={currentStep}
          style={{ marginBottom: 40 }}
          items={[
            {
              title: "登录",
              icon: <UserOutlined />,
            },
            {
              title: "验证码",
              icon: <SafetyOutlined />,
            },
            {
              title: "双因素认证",
              icon: <LockOutlined />,
            },
            {
              title: "完成",
              icon: <CheckCircleOutlined />,
            },
          ]}
        />

        {/* 步骤 0: 输入账号密码 */}
        {currentStep === 0 && (
          <div className="step-content">
            <Alert
              message="安全提示"
              description="您的账号密码将通过加密连接发送到小米服务器进行验证，我们不会保存您的密码。"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Form
              form={form}
              layout="vertical"
              onFinish={handleLogin}
              autoComplete="off"
            >
              <Form.Item
                label="小米账号"
                name="username"
                rules={[{ required: true, message: "请输入小米账号" }]}
              >
                <Input
                  prefix={<UserOutlined />}
                  placeholder="手机号或邮箱"
                  size="large"
                />
              </Form.Item>

              <Form.Item
                label="密码"
                name="password"
                rules={[{ required: true, message: "请输入密码" }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="请输入密码"
                  size="large"
                />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Button onClick={() => navigate("/chat")}>取消</Button>
                  <Button type="primary" htmlType="submit" loading={loading} size="large">
                    下一步
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        )}

        {/* 步骤 1: 输入验证码 */}
        {currentStep === 1 && (
          <div className="step-content">
            <Alert
              message="需要验证码"
              description="为了保护您的账号安全，请输入下方图片中的验证码。"
              type="warning"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <div style={{ textAlign: "center", marginBottom: 24 }}>
              <Image
                src={captchaUrl}
                alt="验证码"
                style={{ maxWidth: "100%", marginBottom: 16 }}
                preview={false}
              />
              <div>
                <Button type="link" onClick={refreshCaptcha}>
                  看不清？换一张
                </Button>
              </div>
            </div>

            <Form
              form={captchaForm}
              layout="vertical"
              onFinish={handleCaptchaSubmit}
            >
              <Form.Item
                label="验证码"
                name="captcha_code"
                rules={[{ required: true, message: "请输入验证码" }]}
              >
                <Input
                  placeholder="请输入图片中的验证码（区分大小写）"
                  size="large"
                  autoFocus
                />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Button onClick={() => setCurrentStep(0)}>返回</Button>
                  <Button type="primary" htmlType="submit" loading={loading} size="large">
                    提交验证码
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        )}

        {/* 步骤 2: 双因素认证 */}
        {currentStep === 2 && (
          <div className="step-content">
            {!showManualInput ? (
              <>
                <Alert
                  message="双因素认证"
                  description={
                    <>
                      <Paragraph style={{ marginBottom: 12 }}>
                        <Text strong>请按以下步骤操作：</Text>
                      </Paragraph>
                      <Paragraph style={{ marginBottom: 8 }}>
                        1. 点击下方按钮打开小米验证页面
                      </Paragraph>
                      <Paragraph style={{ marginBottom: 12 }}>
                        2. 在小米页面点击 <Text mark>"发送验证码"</Text> 按钮
                      </Paragraph>
                      {verifyUrl && (
                        <div style={{ textAlign: 'center', marginBottom: 16 }}>
                          <Button 
                            type="primary"
                            href={verifyUrl} 
                            target="_blank"
                            icon={<SafetyOutlined />}
                            size="large"
                          >
                            打开小米验证页面
                          </Button>
                        </div>
                      )}
                      <Paragraph style={{ marginBottom: 8 }}>
                        3. 查收您<Text strong>{verifyMethod}</Text>的验证码
                      </Paragraph>
                      <Paragraph style={{ marginBottom: 0 }}>
                        4. 在下方输入框中填写收到的<Text mark>6位数字</Text>验证码
                      </Paragraph>
                    </>
                  }
                  type="warning"
                  showIcon
                  style={{ marginBottom: 24 }}
                />

                <Form
                  form={twoFAForm}
                  layout="vertical"
                  onFinish={handle2FASubmit}
                >
                  <Form.Item
                    label="验证码（Ticket）"
                    name="ticket"
                    rules={[
                      { required: true, message: "请输入验证码" },
                      { pattern: /^\d{6}$/, message: "验证码必须为6位数字" }
                    ]}
                  >
                    <Input
                      placeholder="请输入小米发送的6位数字验证码"
                      maxLength={6}
                      size="large"
                      autoFocus
                    />
                  </Form.Item>

                  <Form.Item>
                    <Space style={{ width: "100%", justifyContent: "space-between" }}>
                      <Button onClick={() => navigate("/chat")}>取消</Button>
                      <Space>
                        <Button 
                          onClick={() => handleResend2FACode(false)} 
                          loading={resendingCode}
                          disabled={loading || countdown > 0}
                        >
                          {countdown > 0 ? `重新发送 (${countdown}s)` : "重新发送验证码"}
                        </Button>
                        <Button type="primary" htmlType="submit" loading={loading} size="large">
                          提交验证
                        </Button>
                      </Space>
                    </Space>
                  </Form.Item>

                  <Form.Item>
                    <div style={{ textAlign: 'center', marginTop: 16 }}>
                      <Text type="secondary">验证码无法接收？</Text>
                      <br />
                      <Button type="link" onClick={() => setShowManualInput(true)}>
                        切换到手动输入模式（抓包方式）
                      </Button>
                    </div>
                  </Form.Item>
                </Form>
              </>
            ) : (
              <>
                <Alert
                  message="手动输入凭证"
                  description={
                    <>
                      <Paragraph style={{ marginBottom: 12 }}>
                        <Text strong>抓包步骤：</Text>
                      </Paragraph>
                      <Paragraph style={{ marginBottom: 8 }}>
                        1. 打开抓包工具（如 Charles、Fiddler、浏览器开发者工具等）
                      </Paragraph>
                      <Paragraph style={{ marginBottom: 8 }}>
                        2. 点击下方按钮打开小米验证页面，完成验证
                      </Paragraph>
                      {verifyUrl && (
                        <div style={{ textAlign: 'center', marginBottom: 16 }}>
                          <Button 
                            type="primary"
                            href={verifyUrl} 
                            target="_blank"
                            icon={<SafetyOutlined />}
                            size="large"
                          >
                            打开小米验证页面
                          </Button>
                        </div>
                      )}
                      <Paragraph style={{ marginBottom: 8 }}>
                        3. 在抓包记录中找到请求 <Text code>api.io.mi.com</Text> 的请求
                      </Paragraph>
                      <Paragraph style={{ marginBottom: 8 }}>
                        4. 从请求 Cookie 或响应中提取以下参数：
                      </Paragraph>
                      <Paragraph style={{ marginLeft: 24, marginBottom: 8 }}>
                        • <Text code>ssecurity</Text>（通常在响应中）
                      </Paragraph>
                      <Paragraph style={{ marginLeft: 24, marginBottom: 8 }}>
                        • <Text code>userId</Text>（数字ID）
                      </Paragraph>
                      <Paragraph style={{ marginLeft: 24, marginBottom: 8 }}>
                        • <Text code>cUserId</Text>（长字符串）
                      </Paragraph>
                      <Paragraph style={{ marginLeft: 24, marginBottom: 0 }}>
                        • <Text code>serviceToken</Text>（很长的字符串）
                      </Paragraph>
                    </>
                  }
                  type="info"
                  showIcon
                  style={{ marginBottom: 24 }}
                />

                <Form
                  form={manualForm}
                  layout="vertical"
                  onFinish={handleManualBind}
                  initialValues={{ xiaomi_username: xiaomiUsername }}
                >
                  {!xiaomiUsername && (
                    <Form.Item
                      label="小米账号"
                      name="xiaomi_username"
                      rules={[{ required: true, message: "请输入小米账号" }]}
                    >
                      <Input placeholder="手机号或邮箱" size="large" />
                    </Form.Item>
                  )}

                  <Form.Item
                    label="_ssecurity"
                    name="ssecurity"
                    rules={[{ required: true, message: "请输入_ssecurity参数" }]}
                  >
                    <Input placeholder="例如：R9egnuetTRF9sMP2jy9yJQ==" size="large" />
                  </Form.Item>

                  <Form.Item
                    label="userId"
                    name="userId"
                    rules={[{ required: true, message: "请输入userId参数" }]}
                  >
                    <Input placeholder="例如：3128533266" size="large" />
                  </Form.Item>

                  <Form.Item
                    label="_cUserId"
                    name="cUserId"
                    rules={[{ required: true, message: "请输入_cUserId参数" }]}
                  >
                    <Input placeholder="例如：5suobuxuMCJG7d6Wtp3I28D30l0" size="large" />
                  </Form.Item>

                  <Form.Item
                    label="serviceToken"
                    name="serviceToken"
                    rules={[{ required: true, message: "请输入serviceToken参数" }]}
                  >
                    <Input.TextArea 
                      placeholder="很长的字符串，例如：2ib8u26oDE7OoCSawL3M5rvrIR7koVw..." 
                      rows={4}
                      size="large"
                    />
                  </Form.Item>

                  <Form.Item>
                    <Space style={{ width: "100%", justifyContent: "space-between" }}>
                      <Button onClick={() => setShowManualInput(false)}>返回验证码方式</Button>
                      <Button type="primary" htmlType="submit" loading={loading} size="large">
                        验证并绑定
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>
              </>
            )}
          </div>
        )}

        {/* 步骤 3: 完成 */}
        {currentStep === 3 && (
          <div className="step-content" style={{ textAlign: "center" }}>
            <CheckCircleOutlined
              style={{ fontSize: 72, color: "#52c41a", marginBottom: 24 }}
            />
            <Title level={3}>绑定成功！</Title>
            <Paragraph>
              您的小米账号已成功绑定，现在可以控制您的小米智能设备了。
            </Paragraph>
            <Paragraph type="secondary">
              即将跳转到聊天页面...
            </Paragraph>
            <Button
              type="primary"
              size="large"
              onClick={() => navigate("/chat")}
              style={{ marginTop: 24 }}
            >
              立即开始
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
};

export default XiaomiBinding;

