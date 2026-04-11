import React, { useState, useEffect, useMemo } from "react";
import { Card, Button, message, Space, Typography, Tag, Spin, Modal, Form, Input, Drawer, Row, Col } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LinkOutlined,
  ExclamationCircleOutlined,
  HomeOutlined,
  CheckSquareOutlined,
  RocketOutlined,
  CloudOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { checkXiaomiBindingStatus, unbindXiaomiAccount, type BindingStatus } from "../../api/xiaomi";
import { checkDidaBindingStatus, unbindDidaAccount, type DidaBindingStatusResponse } from "../../api/dida";
import type { UserInfo } from "../../api/auth";
import { getClawSettings, setClawSettings, isValidEmbedUrl } from "../../utils/clawSettings";

const { Text, Paragraph } = Typography;

export interface BindingSectionProps {
  userInfo: UserInfo | null;
}

type ConfigKey = "xiaomi" | "dida" | "openclaw" | "zeroclaw";

const BindingSection: React.FC<BindingSectionProps> = ({ userInfo }) => {
  const navigate = useNavigate();
  const [openClawForm] = Form.useForm();
  const [zeroClawForm] = Form.useForm();
  const [xiaomiLoading, setXiaomiLoading] = useState(false);
  const [didaLoading, setDidaLoading] = useState(false);
  const [bindingStatus, setBindingStatus] = useState<BindingStatus | null>(null);
  const [didaBindingStatus, setDidaBindingStatus] = useState<DidaBindingStatusResponse | null>(null);
  const [activeConfig, setActiveConfig] = useState<ConfigKey | null>(null);
  const [clawSettingsVersion, setClawSettingsVersion] = useState(0);

  useEffect(() => {
    void loadBindingStatus();
    void loadDidaBindingStatus();
  }, [userInfo?.id]);

  useEffect(() => {
    const onClawChanged = () => setClawSettingsVersion((v) => v + 1);
    window.addEventListener("clawSettingsChanged", onClawChanged);
    return () => window.removeEventListener("clawSettingsChanged", onClawChanged);
  }, []);

  useEffect(() => {
    if (!userInfo?.id) return;
    const s = getClawSettings(userInfo.id);
    openClawForm.setFieldsValue({ openclawUrl: s.openclawUrl });
    zeroClawForm.setFieldsValue({ zeroclawUrl: s.zeroclawUrl });
  }, [userInfo?.id, openClawForm, zeroClawForm]);

  const loadBindingStatus = async () => {
    if (!userInfo) return;
    try {
      setXiaomiLoading(true);
      const status = await checkXiaomiBindingStatus(userInfo.id);
      setBindingStatus(status);
    } catch (error: unknown) {
      console.error("加载小米账号绑定状态失败:", error);
      message.error("加载小米绑定状态失败");
    } finally {
      setXiaomiLoading(false);
    }
  };

  const loadDidaBindingStatus = async () => {
    if (!userInfo) return;
    try {
      setDidaLoading(true);
      const status = await checkDidaBindingStatus(userInfo.id);
      setDidaBindingStatus(status);
    } catch (error: unknown) {
      console.error("加载滴答清单绑定状态失败:", error);
      message.error("加载滴答清单绑定状态失败");
    } finally {
      setDidaLoading(false);
    }
  };

  const handleBindXiaomi = () => navigate("/xiaomi-binding");

  const handleUnbindXiaomi = () => {
    if (!userInfo) return;
    Modal.confirm({
      title: "确认解绑小米账号",
      icon: <ExclamationCircleOutlined />,
      content: "解绑后，将无法通过 Moss AI 助手控制小米智能家居设备。您确定要解绑吗？",
      okText: "确认解绑",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await unbindXiaomiAccount(userInfo.id);
          message.success("小米账号已解绑");
          void loadBindingStatus();
        } catch (error: unknown) {
          console.error("解绑小米账号失败:", error);
          const err = error as { response?: { data?: { detail?: string } } };
          message.error(err.response?.data?.detail || "解绑失败，请稍后重试");
        }
      },
    });
  };

  const handleBindDida = () => navigate("/dida-binding");

  const handleSaveOpenClaw = async () => {
    if (!userInfo) return;
    try {
      const v = await openClawForm.validateFields();
      const openclawUrl = String(v.openclawUrl ?? "").trim();
      if (!isValidEmbedUrl(openclawUrl)) {
        message.error("地址需为 http:// 或 https:// 开头的合法 URL");
        return;
      }
      const prev = getClawSettings(userInfo.id);
      setClawSettings(userInfo.id, { openclawUrl, zeroclawUrl: prev.zeroclawUrl });
      message.success("OpenClaw 地址已保存");
    } catch {
      /* 表单校验未通过 */
    }
  };

  const handleSaveZeroClaw = async () => {
    if (!userInfo) return;
    try {
      const v = await zeroClawForm.validateFields();
      const zeroclawUrl = String(v.zeroclawUrl ?? "").trim();
      if (!isValidEmbedUrl(zeroclawUrl)) {
        message.error("地址需为 http:// 或 https:// 开头的合法 URL");
        return;
      }
      const prev = getClawSettings(userInfo.id);
      setClawSettings(userInfo.id, { openclawUrl: prev.openclawUrl, zeroclawUrl });
      message.success("ZeroClaw 地址已保存");
    } catch {
      /* 表单校验未通过 */
    }
  };

  const handleUnbindDida = () => {
    if (!userInfo) return;
    Modal.confirm({
      title: "确认解绑滴答清单账号",
      icon: <ExclamationCircleOutlined />,
      content: "解绑后，将无法通过 Moss AI 助手管理您的滴答清单任务。您确定要解绑吗？",
      okText: "确认解绑",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await unbindDidaAccount(userInfo.id);
          message.success("滴答清单账号已解绑");
          void loadDidaBindingStatus();
        } catch (error: unknown) {
          console.error("解绑滴答清单账号失败:", error);
          const err = error as { response?: { data?: { detail?: string } } };
          message.error(err.response?.data?.detail || "解绑失败，请稍后重试");
        }
      },
    });
  };

  const openClawConfigured = useMemo(() => {
    if (!userInfo?.id) return false;
    const o = String(getClawSettings(userInfo.id).openclawUrl ?? "").trim();
    return o.length > 0 && isValidEmbedUrl(o);
  }, [userInfo?.id, clawSettingsVersion]);

  const zeroClawConfigured = useMemo(() => {
    if (!userInfo?.id) return false;
    const z = String(getClawSettings(userInfo.id).zeroclawUrl ?? "").trim();
    return z.length > 0 && isValidEmbedUrl(z);
  }, [userInfo?.id, clawSettingsVersion]);

  const drawerTitles: Record<ConfigKey, string> = {
    xiaomi: "小米账号",
    dida: "滴答清单",
    openclaw: "OpenClaw 嵌入",
    zeroclaw: "ZeroClaw 嵌入",
  };

  const renderXiaomiDetail = () => (
    <Spin spinning={xiaomiLoading}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div className="status-row">
          <Text strong>绑定状态：</Text>
          {bindingStatus?.is_bound ? (
            <Tag icon={<CheckCircleOutlined />} color="success">
              已绑定
            </Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">
              未绑定
            </Tag>
          )}
        </div>

        {bindingStatus?.is_bound && (
          <>
            <div className="status-row">
              <Text strong>小米账号：</Text>
              <Text>{bindingStatus.username}</Text>
            </div>
            {bindingStatus.bound_at && (
              <div className="status-row">
                <Text strong>绑定时间：</Text>
                <Text type="secondary">{new Date(bindingStatus.bound_at).toLocaleString("zh-CN")}</Text>
              </div>
            )}
            <div className="rebind-section">
              <Space wrap>
                <Button type="default" onClick={handleBindXiaomi}>
                  重新绑定
                </Button>
                <Button danger onClick={handleUnbindXiaomi}>
                  解绑账号
                </Button>
              </Space>
              <Text type="secondary" style={{ marginTop: 8, display: "block" }}>
                解绑后需重新授权才能使用相关功能
              </Text>
            </div>
          </>
        )}

        {!bindingStatus?.is_bound && (
          <div className="binding-hint">
            <Text type="secondary">绑定小米账号后，您可以通过 Moss AI 控制小米智能家居设备</Text>
          </div>
        )}

        {!bindingStatus?.is_bound && (
          <Button type="primary" icon={<LinkOutlined />} block onClick={handleBindXiaomi}>
            绑定小米账号
          </Button>
        )}
      </Space>
    </Spin>
  );

  const renderDidaDetail = () => (
    <Spin spinning={didaLoading}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div className="status-row">
          <Text strong>绑定状态：</Text>
          {didaBindingStatus?.is_bound ? (
            <Tag icon={<CheckCircleOutlined />} color="success">
              已绑定
            </Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">
              未绑定
            </Tag>
          )}
        </div>

        {didaBindingStatus?.is_bound && (
          <>
            <div className="status-row">
              <Text strong>滴答清单账号：</Text>
              <Text>{didaBindingStatus.username}</Text>
            </div>
            {didaBindingStatus.bound_at && (
              <div className="status-row">
                <Text strong>绑定时间：</Text>
                <Text type="secondary">{new Date(didaBindingStatus.bound_at).toLocaleString("zh-CN")}</Text>
              </div>
            )}
            {didaBindingStatus.token_expires_at && (
              <div className="status-row">
                <Text strong>令牌过期时间：</Text>
                <Text type="secondary">
                  {new Date(didaBindingStatus.token_expires_at).toLocaleString("zh-CN")}
                </Text>
              </div>
            )}
            <div className="rebind-section">
              <Space wrap>
                <Button type="default" onClick={handleBindDida}>
                  重新绑定
                </Button>
                <Button danger onClick={handleUnbindDida}>
                  解绑账号
                </Button>
              </Space>
              <Text type="secondary" style={{ marginTop: 8, display: "block" }}>
                解绑后需重新授权才能使用相关功能
              </Text>
            </div>
          </>
        )}

        {!didaBindingStatus?.is_bound && (
          <div className="binding-hint">
            <Text type="secondary">
              绑定滴答清单账号后，您可以通过 Moss AI 助手管理您的待办事项、创建任务等
            </Text>
          </div>
        )}

        {!didaBindingStatus?.is_bound && (
          <Button type="primary" icon={<LinkOutlined />} block onClick={handleBindDida}>
            绑定滴答清单
          </Button>
        )}
      </Space>
    </Spin>
  );

  const renderOpenClawDetail = () => (
    <>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        填写 OpenClaw 的 Web 地址后，侧边栏会出现「OpenClaw」入口。地址保存在本机浏览器；ZeroClaw 在另一项中单独配置。
      </Paragraph>
      <Form form={openClawForm} layout="vertical">
        <Form.Item
          name="openclawUrl"
          label="OpenClaw 页面地址"
          rules={[
            {
              validator: async (_, value: string) => {
                const t = String(value ?? "").trim();
                if (!t) return;
                if (!isValidEmbedUrl(t)) throw new Error("请输入以 http:// 或 https:// 开头的地址");
              },
            },
          ]}
        >
          <Input allowClear placeholder="例如 https://openclaw.example.com" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" onClick={() => void handleSaveOpenClaw()}>
            保存
          </Button>
        </Form.Item>
      </Form>
    </>
  );

  const renderZeroClawDetail = () => (
    <>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        填写 ZeroClaw 的 Web 地址后，侧边栏会出现「ZeroClaw」入口。地址保存在本机浏览器；OpenClaw 在另一项中单独配置。
      </Paragraph>
      <Form form={zeroClawForm} layout="vertical">
        <Form.Item
          name="zeroclawUrl"
          label="ZeroClaw 页面地址"
          rules={[
            {
              validator: async (_, value: string) => {
                const t = String(value ?? "").trim();
                if (!t) return;
                if (!isValidEmbedUrl(t)) throw new Error("请输入以 http:// 或 https:// 开头的地址");
              },
            },
          ]}
        >
          <Input allowClear placeholder="例如 https://zeroclaw.example.com" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" onClick={() => void handleSaveZeroClaw()}>
            保存
          </Button>
        </Form.Item>
      </Form>
    </>
  );

  const catalogItems: {
    key: ConfigKey;
    title: string;
    blurb: string;
    icon: React.ReactNode;
    bound: boolean;
    loading: boolean;
  }[] = [
    {
      key: "xiaomi",
      title: "小米账号",
      blurb: "智能家居与设备联动，语音与场景控制",
      icon: <HomeOutlined />,
      bound: Boolean(bindingStatus?.is_bound),
      loading: xiaomiLoading,
    },
    {
      key: "dida",
      title: "滴答清单",
      blurb: "待办与任务同步，像清单插件一样接入助手",
      icon: <CheckSquareOutlined />,
      bound: Boolean(didaBindingStatus?.is_bound),
      loading: didaLoading,
    },
    {
      key: "openclaw",
      title: "OpenClaw",
      blurb: "OpenClaw 页面嵌入侧边栏，与 ZeroClaw 分开配置",
      icon: <RocketOutlined />,
      bound: openClawConfigured,
      loading: false,
    },
    {
      key: "zeroclaw",
      title: "ZeroClaw",
      blurb: "ZeroClaw 页面嵌入侧边栏，与 OpenClaw 分开配置",
      icon: <CloudOutlined />,
      bound: zeroClawConfigured,
      loading: false,
    },
  ];

  return (
    <>
      <Card className="config-catalog-card" bordered={false}>
        <Paragraph type="secondary" className="config-catalog-intro">
          以下为可启用的集成项，点击缩略块查看授权、账号与地址等详细设置（类似插件管理）。
        </Paragraph>
        <Row gutter={[16, 16]}>
          {catalogItems.map((item) => (
            <Col xs={24} sm={12} lg={8} key={item.key}>
              <button
                type="button"
                className="config-tile"
                onClick={() => setActiveConfig(item.key)}
                aria-label={`打开 ${item.title} 配置`}
              >
                <Spin spinning={item.loading}>
                  <div className="config-tile-inner">
                    <div className="config-tile-icon">{item.icon}</div>
                    <div className="config-tile-body">
                      <div className="config-tile-title-row">
                        <Text strong className="config-tile-title">
                          {item.title}
                        </Text>
                        {item.bound ? (
                          <Tag icon={<CheckCircleOutlined />} color="success" className="config-tile-tag">
                            已启用
                          </Tag>
                        ) : (
                          <Tag color="default" className="config-tile-tag">
                            未配置
                          </Tag>
                        )}
                      </div>
                      <Text type="secondary" className="config-tile-desc" ellipsis={{ rows: 2 }}>
                        {item.blurb}
                      </Text>
                    </div>
                    <RightOutlined className="config-tile-chevron" aria-hidden />
                  </div>
                </Spin>
              </button>
            </Col>
          ))}
        </Row>
      </Card>

      <Drawer
        title={activeConfig ? drawerTitles[activeConfig] : ""}
        placement="right"
        width={Math.min(520, typeof window !== "undefined" ? window.innerWidth - 24 : 520)}
        open={activeConfig !== null}
        onClose={() => setActiveConfig(null)}
        destroyOnClose
        className="config-detail-drawer"
      >
        {activeConfig === "xiaomi" && renderXiaomiDetail()}
        {activeConfig === "dida" && renderDidaDetail()}
        {activeConfig === "openclaw" && renderOpenClawDetail()}
        {activeConfig === "zeroclaw" && renderZeroClawDetail()}
      </Drawer>
    </>
  );
};

export default BindingSection;
