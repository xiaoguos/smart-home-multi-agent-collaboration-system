import React, { useState, useEffect, useRef } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  Steps,
  message,
  Alert,
  Typography,
  Space,
} from "antd";
import {
  CheckCircleOutlined,
  LinkOutlined,
  SafetyOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import {
  handleDidaOAuthCallback,
  getDidaOAuthUrl,
} from "../api/dida";
import "./style/xiaomi-binding.sass"; // 复用小米绑定的样式

const { Title, Text, Paragraph } = Typography;

const DidaBinding: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [clientId, setClientId] = useState<string>("");
  const [clientSecret, setClientSecret] = useState<string>("");
  const [authorizationCode, setAuthorizationCode] = useState<string>("");
  const [oauthUrl, setOauthUrl] = useState<string>("");
  
  // 使用useRef而不是useState，立即生效，避免React渲染延迟导致重复请求
  const isProcessingRef = useRef(false);
  const processedCodeRef = useRef<string | null>(null);

  /**
   * 检查URL中是否有授权码（OAuth回调）
   * 关键优化：检测到code后立即清除URL，防止React StrictMode导致的重复触发
   */
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get("code");
    
    // 严格的防重复检查：只用processedCodeRef，让handleOAuthCallback管理isProcessingRef
    if (code && code !== processedCodeRef.current) {
      console.log('✅ 检测到OAuth回调，code:', code);
      
      // 记录已处理的code，防止重复
      processedCodeRef.current = code;
      setAuthorizationCode(code);
      
      // 注意：不要立即清除URL，保留code参数供后续处理
      // URL清除会在成功绑定后进行
      
      // 从localStorage恢复Client凭证
      const savedClientId = localStorage.getItem("dida_client_id");
      const savedClientSecret = localStorage.getItem("dida_client_secret");
      
      if (savedClientId && savedClientSecret) {
        setClientId(savedClientId);
        setClientSecret(savedClientSecret);
        setCurrentStep(2); // 跳到第3步（处理授权）
        
        // 立即调用，不需要延迟
        handleOAuthCallback(savedClientId, savedClientSecret, code);
      } else {
        message.error("未找到Client凭证，请重新开始绑定流程");
        setCurrentStep(0);
        processedCodeRef.current = null;
      }
    }
  }, [location.search]); // 只依赖search参数

  /**
   * 步骤1：输入Client ID和Secret
   */
  const handleSubmitCredentials = async (values: { client_id: string; client_secret: string }) => {
    setLoading(true);
    try {
      const cid = values.client_id.trim();
      const secret = values.client_secret.trim();
      
      // 保存到状态和localStorage
      setClientId(cid);
      setClientSecret(secret);
      localStorage.setItem("dida_client_id", cid);
      localStorage.setItem("dida_client_secret", secret);
      
      // 生成OAuth授权URL
      const authUrl = getDidaOAuthUrl(cid);
      setOauthUrl(authUrl);
      
      // 输出调试信息
      console.log('=== 滴答清单OAuth调试信息 ===');
      console.log('当前应用地址:', window.location.origin);
      console.log('回调地址:', `${window.location.origin}/dida-binding`);
      console.log('OAuth URL:', authUrl);
      console.log('请确保在滴答清单开放平台配置的回调地址与上面的"回调地址"完全一致！');
      console.log('===========================');
      
      setCurrentStep(1);
      message.success("请点击下方按钮进行授权");
    } catch (error: any) {
      message.error(error.response?.data?.detail || "保存失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  /**
   * 步骤2：处理OAuth回调
   */
  const handleOAuthCallback = async (cid: string, secret: string, code: string) => {
    // 防重复检查：只检查loading状态
    if (loading) {
      console.log('⚠️ 正在处理中，跳过重复请求');
      return;
    }
    
    console.log('🚀 开始处理OAuth回调...');
    setLoading(true);
    isProcessingRef.current = true; // 标记正在处理
    
    try {
      // 从 localStorage 获取用户信息
      const userStr = localStorage.getItem('user_info');
      if (!userStr) {
        message.error('请先登录系统账号');
        navigate('/');
        return;
      }
      
      const user = JSON.parse(userStr);
      
      // 构造redirect_uri，必须与OAuth授权时一致
      const redirectUri = `${window.location.origin}/dida-binding`;
      
      console.log('提交OAuth回调，redirect_uri:', redirectUri);
      
      const response = await handleDidaOAuthCallback({
        system_user_id: user.id,
        client_id: cid,
        client_secret: secret,
        authorization_code: code,
        redirect_uri: redirectUri,
      });

      console.log('OAuth回调响应:', response);

      if (response.status === "success") {
        message.success(response.message);
        
        // 清理localStorage中的临时数据
        localStorage.removeItem("dida_client_id");
        localStorage.removeItem("dida_client_secret");
        
        // 清除URL中的code参数
        window.history.replaceState({}, '', '/dida-binding');
        
        setCurrentStep(3);
        
        // 立即跳转到聊天页面
        setTimeout(() => {
          navigate("/chat");
        }, 1500);
      } else {
        message.error(response.message || "绑定失败");
        setCurrentStep(0);
        // 重置处理状态
        isProcessingRef.current = false;
        processedCodeRef.current = null;
      }
    } catch (error: any) {
      console.error('❌ OAuth回调错误:', error);
      const errorMsg = error.response?.data?.detail || error.message || "绑定失败，请稍后重试";
      message.error(errorMsg);
      setCurrentStep(0);
      // 重置处理状态
      isProcessingRef.current = false;
      processedCodeRef.current = null;
    } finally {
      setLoading(false);
    }
  };

  /**
   * 打开OAuth授权页面（在当前标签页）
   */
  const openOAuthPage = () => {
    if (oauthUrl) {
      window.location.href = oauthUrl;
    }
  };

  return (
    <div className="xiaomi-binding-container">
      <Card className="binding-card">
        <Title level={2} style={{ textAlign: "center", marginBottom: 30 }}>
          绑定滴答清单账号
        </Title>

        <Steps
          current={currentStep}
          style={{ marginBottom: 40 }}
          items={[
            {
              title: "配置应用",
              icon: <SafetyOutlined />,
            },
            {
              title: "OAuth授权",
              icon: <LinkOutlined />,
            },
            {
              title: "处理回调",
              icon: <SafetyOutlined />,
            },
            {
              title: "完成",
              icon: <CheckCircleOutlined />,
            },
          ]}
        />

        {/* 步骤 0: 输入Client ID和Secret */}
        {currentStep === 0 && (
          <div className="step-content">
            <Alert
              message="配置说明"
              description={
                <>
                  <Paragraph style={{ marginBottom: 12 }}>
                    <Text strong>请按照以下步骤获取滴答清单应用凭证：</Text>
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    1. 访问{" "}
                    <a href="https://developer.dida365.com" target="_blank" rel="noopener noreferrer">
                      滴答清单开放平台
                    </a>
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    2. 创建一个应用，填写应用名称
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    3. 在应用设置中，将 <Text mark>OAuth Redirect URL</Text> 设置为：
                    <br />
                    <Text code style={{ 
                      backgroundColor: '#fffbe6', 
                      border: '1px solid #ffe58f',
                      padding: '4px 8px',
                      fontSize: '14px',
                      fontWeight: 'bold'
                    }}>
                      {window.location.origin}/dida-binding
                    </Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      ⚠️ 请精确复制此地址，不要有多余空格！当前端口是 {window.location.port}
                    </Text>
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    4. 复制应用的 <Text strong>Client ID</Text> 和 <Text strong>Client Secret</Text>
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 0 }}>
                    5. 在下方输入框中填写这两个参数
                  </Paragraph>
                </>
              }
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmitCredentials}
              autoComplete="off"
            >
              <Form.Item
                label="Client ID"
                name="client_id"
                rules={[{ required: true, message: "请输入Client ID" }]}
              >
                <Input placeholder="请输入滴答清单应用的Client ID" size="large" />
              </Form.Item>

              <Form.Item
                label="Client Secret"
                name="client_secret"
                rules={[{ required: true, message: "请输入Client Secret" }]}
              >
                <Input.Password placeholder="请输入滴答清单应用的Client Secret" size="large" />
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

        {/* 步骤 1: OAuth授权 */}
        {currentStep === 1 && (
          <div className="step-content">
            <Alert
              message="OAuth授权"
              description={
                <>
                  <Paragraph style={{ marginBottom: 12 }}>
                    <Text strong>请点击下方按钮打开滴答清单授权页面：</Text>
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    1. 在授权页面登录您的滴答清单账号
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    2. 授权应用访问您的任务数据
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    3. 授权成功后，页面会自动跳转回本页面
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 0 }}>
                    4. 系统将自动完成绑定流程
                  </Paragraph>
                </>
              }
              type="warning"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <div style={{ textAlign: "center", marginBottom: 24 }}>
              <Button
                type="primary"
                size="large"
                icon={<LinkOutlined />}
                onClick={openOAuthPage}
              >
                打开滴答清单授权页面
              </Button>
            </div>

            <Alert
              message="提示"
              description="如果授权页面没有自动打开，请手动复制以下链接到浏览器："
              type="info"
              style={{ marginBottom: 16 }}
            />
            <Input.TextArea
              value={oauthUrl}
              readOnly
              rows={3}
              style={{ marginBottom: 24 }}
            />

            <Space style={{ width: "100%", justifyContent: "space-between" }}>
              <Button onClick={() => setCurrentStep(0)}>返回</Button>
              <Text type="secondary">等待授权...</Text>
            </Space>
          </div>
        )}

        {/* 步骤 2: 处理回调 */}
        {currentStep === 2 && (
          <div className="step-content" style={{ textAlign: "center" }}>
            <Alert
              message="正在处理授权..."
              description="请稍候，系统正在完成绑定流程"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />
            <Button type="primary" loading>
              处理中
            </Button>
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
              您的滴答清单账号已成功绑定，现在可以通过AI助手管理您的待办事项了。
            </Paragraph>
            <Paragraph type="secondary">即将跳转到聊天页面...</Paragraph>
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

export default DidaBinding;

