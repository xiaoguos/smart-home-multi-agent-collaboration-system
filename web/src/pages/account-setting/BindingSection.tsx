import React, { useState, useEffect, useMemo } from "react";
import {
  Card,
  Button,
  message,
  Space,
  Typography,
  Tag,
  Spin,
  Modal,
  Form,
  Input,
  Drawer,
  Row,
  Col,
  Switch,
  Select,
  InputNumber,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LinkOutlined,
  ExclamationCircleOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { checkXiaomiBindingStatus, unbindXiaomiAccount, type BindingStatus } from "../../api/xiaomi";
import { checkDidaBindingStatus, unbindDidaAccount, type DidaBindingStatusResponse } from "../../api/dida";
import type { UserInfo } from "../../api/auth";
import {
  getAudioPluginMcpConfig,
  getCameraPluginConfig,
  getPluginModes,
  getSystemConfig,
  testAudioPluginOutput,
  updateAudioPluginMcpConfig,
  updateCameraPluginConfig,
  updatePluginMode,
  updateSystemConfig,
  type AudioPluginMcpConfig,
  type CameraPluginConfig,
  type PluginMode,
} from "../../api/config";
import { setClawSettings, isValidEmbedUrl } from "../../utils/clawSettings";
import { ACCOUNT_SETTING_PLUGINS, type ConfigPluginKey } from "./pluginRegistry";
import "./account-setting.sass";

const { Text, Paragraph } = Typography;

const DEFAULT_PLUGIN_MODES: Record<ConfigPluginKey, PluginMode["mode"]> = {
  xiaomi: "unused",
  dida: "unused",
  wechat: "unused",
  openclaw: "unused",
  zeroclaw: "unused",
  camera: "unused",
  audio: "unused",
};

function normalizePluginMode(mode: unknown): PluginMode["mode"] {
  const value = String(mode ?? "").trim().toLowerCase();
  if (value === "enabled" || value === "disabled" || value === "unused") return value;
  return "unused";
}

function isStrictHttpUrl(url: string): boolean {
  const trimmed = String(url ?? "").trim();
  return trimmed.length > 0 && isValidEmbedUrl(trimmed);
}

export interface BindingSectionProps {
  userInfo: UserInfo | null;
}

const BindingSection: React.FC<BindingSectionProps> = ({ userInfo }) => {
  const navigate = useNavigate();
  const [openClawForm] = Form.useForm();
  const [zeroClawForm] = Form.useForm();
  const [cameraForm] = Form.useForm();
  const [audioForm] = Form.useForm();

  const [catalogLoading, setCatalogLoading] = useState(false);
  const [modeUpdatingKey, setModeUpdatingKey] = useState<ConfigPluginKey | null>(null);
  const [xiaomiLoading, setXiaomiLoading] = useState(false);
  const [didaLoading, setDidaLoading] = useState(false);
  const [cameraSaving, setCameraSaving] = useState(false);
  const [audioSaving, setAudioSaving] = useState(false);
  const [audioTesting, setAudioTesting] = useState(false);

  const [bindingStatus, setBindingStatus] = useState<BindingStatus | null>(null);
  const [didaBindingStatus, setDidaBindingStatus] = useState<DidaBindingStatusResponse | null>(null);
  const [pluginModes, setPluginModes] = useState<Record<ConfigPluginKey, PluginMode["mode"]>>(DEFAULT_PLUGIN_MODES);
  const [openclawUrl, setOpenclawUrl] = useState("");
  const [zeroclawUrl, setZeroclawUrl] = useState("");
  const [cameraConfig, setCameraConfig] = useState<CameraPluginConfig>({
    source: "local",
    local_index: 0,
    remote_url: "",
  });
  const [audioConfig, setAudioConfig] = useState<AudioPluginMcpConfig>({
    enabled: false,
    command: "",
    args: [],
    cwd: "",
    env: {},
  });
  const [activeConfig, setActiveConfig] = useState<ConfigPluginKey | null>(null);

  const cameraSource = Form.useWatch("source", cameraForm) as CameraPluginConfig["source"] | undefined;
  const effectiveCameraSource = cameraSource || cameraConfig.source || "local";

  const syncClawLocalCache = (
    nextOpenUrl: string,
    nextZeroUrl: string,
    nextModes: Record<ConfigPluginKey, PluginMode["mode"]>,
  ) => {
    if (!userInfo?.id) return;
    setClawSettings(userInfo.id, {
      openclawUrl: nextOpenUrl,
      zeroclawUrl: nextZeroUrl,
      openclawEnabled: nextModes.openclaw === "enabled",
      zeroclawEnabled: nextModes.zeroclaw === "enabled",
    });
  };

  const getPluginMode = (pluginKey: ConfigPluginKey): PluginMode["mode"] =>
    normalizePluginMode(pluginModes[pluginKey]);

  const isPluginEnabled = (pluginKey: ConfigPluginKey): boolean => getPluginMode(pluginKey) === "enabled";

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

  const safeLoadConfigValue = async (configKey: string): Promise<string> => {
    try {
      const result = await getSystemConfig(configKey);
      const value = result?.config_value;
      return value === undefined || value === null ? "" : String(value).trim();
    } catch (error: unknown) {
      const err = error as { response?: { status?: number } };
      if (err.response?.status === 404) return "";
      throw error;
    }
  };

  const loadPluginModes = async () => {
    const rows = await getPluginModes();
    const nextModes: Record<ConfigPluginKey, PluginMode["mode"]> = { ...DEFAULT_PLUGIN_MODES };
    rows.forEach((row) => {
      const key = String(row.plugin_key || "").trim().toLowerCase();
      if (key in nextModes) {
        nextModes[key as ConfigPluginKey] = normalizePluginMode(row.mode);
      }
    });
    setPluginModes(nextModes);
    return nextModes;
  };

  const loadPluginConfigs = async (modesForSync: Record<ConfigPluginKey, PluginMode["mode"]>) => {
    const [loadedOpenclawUrl, loadedZeroclawUrl, loadedCamera, loadedAudio] = await Promise.all([
      safeLoadConfigValue("plugin.openclaw.url"),
      safeLoadConfigValue("plugin.zeroclaw.url"),
      getCameraPluginConfig(),
      getAudioPluginMcpConfig(),
    ]);
    setOpenclawUrl(loadedOpenclawUrl);
    setZeroclawUrl(loadedZeroclawUrl);
    setCameraConfig(loadedCamera);
    setAudioConfig(loadedAudio);
    openClawForm.setFieldsValue({ openclawUrl: loadedOpenclawUrl });
    zeroClawForm.setFieldsValue({ zeroclawUrl: loadedZeroclawUrl });
    cameraForm.setFieldsValue(loadedCamera);
    audioForm.setFieldsValue({
      enabled: loadedAudio.enabled,
      command: loadedAudio.command,
      argsText: JSON.stringify(loadedAudio.args ?? []),
      cwd: loadedAudio.cwd,
      envText: JSON.stringify(loadedAudio.env ?? {}, null, 2),
    });
    syncClawLocalCache(loadedOpenclawUrl, loadedZeroclawUrl, modesForSync);
  };

  const reloadAll = async () => {
    setCatalogLoading(true);
    try {
      await Promise.all([loadBindingStatus(), loadDidaBindingStatus()]);
      const modes = await loadPluginModes();
      await loadPluginConfigs(modes);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`加载插件配置失败: ${msg}`);
    } finally {
      setCatalogLoading(false);
    }
  };

  useEffect(() => {
    if (!userInfo?.id) return;
    void reloadAll();
  }, [userInfo?.id]);

  const setPluginEnable = async (pluginKey: ConfigPluginKey, enabled: boolean) => {
    try {
      setModeUpdatingKey(pluginKey);
      const updated = await updatePluginMode(pluginKey, enabled ? "enabled" : "disabled");
      const nextModes = {
        ...pluginModes,
        [pluginKey]: normalizePluginMode(updated.mode),
      };
      setPluginModes(nextModes);
      if (pluginKey === "openclaw" || pluginKey === "zeroclaw") {
        syncClawLocalCache(openclawUrl, zeroclawUrl, nextModes);
      }
      message.success("插件开启状态已更新");
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`更新插件开启状态失败: ${msg}`);
    } finally {
      setModeUpdatingKey(null);
    }
  };

  const ensureEnabledAfterBinding = async (pluginKey: ConfigPluginKey) => {
    if (isPluginEnabled(pluginKey)) return;
    await setPluginEnable(pluginKey, true);
  };

  const handleBindXiaomi = () => navigate("/xiaomi-binding");

  const handleUnbindXiaomi = () => {
    if (!userInfo) return;
    Modal.confirm({
      title: "确认解绑小米账号",
      icon: <ExclamationCircleOutlined />,
      content: "解绑后，将无法通过智能管家系统 助手控制小米智能家居设备。您确定要解绑吗？",
      okText: "确认解绑",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await unbindXiaomiAccount(userInfo.id);
          message.success("小米账号已解绑");
          void loadBindingStatus();
        } catch (error: unknown) {
          const err = error as { response?: { data?: { detail?: string } } };
          message.error(err.response?.data?.detail || "解绑失败，请稍后重试");
        }
      },
    });
  };

  const handleBindDida = () => navigate("/dida-binding");

  const handleUnbindDida = () => {
    if (!userInfo) return;
    Modal.confirm({
      title: "确认解绑滴答清单账号",
      icon: <ExclamationCircleOutlined />,
      content: "解绑后，将无法通过智能管家系统 助手管理您的滴答清单任务。您确定要解绑吗？",
      okText: "确认解绑",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await unbindDidaAccount(userInfo.id);
          message.success("滴答清单账号已解绑");
          void loadDidaBindingStatus();
        } catch (error: unknown) {
          const err = error as { response?: { data?: { detail?: string } } };
          message.error(err.response?.data?.detail || "解绑失败，请稍后重试");
        }
      },
    });
  };

  const handleSaveOpenClaw = async () => {
    try {
      const values = await openClawForm.validateFields();
      const nextUrl = String(values.openclawUrl ?? "").trim();
      const wasBound = isStrictHttpUrl(openclawUrl);
      if (nextUrl && !isValidEmbedUrl(nextUrl)) {
        message.error("请输入合法的 OpenClaw 地址");
        return;
      }
      await updateSystemConfig("plugin.openclaw.url", nextUrl);
      setOpenclawUrl(nextUrl);
      syncClawLocalCache(nextUrl, zeroclawUrl, pluginModes);
      if (!wasBound && isStrictHttpUrl(nextUrl)) {
        await ensureEnabledAfterBinding("openclaw");
      }
      message.success("OpenClaw 配置已保存");
    } catch {
      // 表单校验失败
    }
  };

  const handleSaveZeroClaw = async () => {
    try {
      const values = await zeroClawForm.validateFields();
      const nextUrl = String(values.zeroclawUrl ?? "").trim();
      const wasBound = isStrictHttpUrl(zeroclawUrl);
      if (nextUrl && !isValidEmbedUrl(nextUrl)) {
        message.error("请输入合法的 ZeroClaw 地址");
        return;
      }
      await updateSystemConfig("plugin.zeroclaw.url", nextUrl);
      setZeroclawUrl(nextUrl);
      syncClawLocalCache(openclawUrl, nextUrl, pluginModes);
      if (!wasBound && isStrictHttpUrl(nextUrl)) {
        await ensureEnabledAfterBinding("zeroclaw");
      }
      message.success("ZeroClaw 配置已保存");
    } catch {
      // 表单校验失败
    }
  };

  const handleSaveCameraConfig = async () => {
    try {
      const values = await cameraForm.validateFields();
      const source = values.source as CameraPluginConfig["source"];
      const localIndex = Number(values.local_index ?? 0);
      const remoteUrl = String(values.remote_url ?? "").trim();
      const wasBound = cameraConfig.source === "local" ? true : isStrictHttpUrl(cameraConfig.remote_url || "");
      if (source === "remote" && !isStrictHttpUrl(remoteUrl)) {
        message.error("远程摄像头地址必须为有效的 http/https URL");
        return;
      }
      setCameraSaving(true);
      const updated = await updateCameraPluginConfig({
        source,
        local_index: localIndex,
        remote_url: remoteUrl,
      });
      setCameraConfig(updated);
      const nextBound = source === "local" ? true : isStrictHttpUrl(remoteUrl);
      if ((!wasBound || getPluginMode("camera") === "unused") && nextBound) {
        await ensureEnabledAfterBinding("camera");
      }
      message.success("摄像头插件配置已保存");
    } catch {
      // 表单校验失败
    } finally {
      setCameraSaving(false);
    }
  };

  const handleSaveAudioMcpConfig = async () => {
    try {
      const values = await audioForm.validateFields();
      const cmd = String(values.command ?? "").trim();
      const enabled = Boolean(values.enabled);
      let args: string[] = [];
      try {
        const parsed = JSON.parse(String(values.argsText ?? "").trim() || "[]");
        if (!Array.isArray(parsed)) throw new Error();
        args = parsed.map((x) => String(x));
      } catch {
        message.error("启动参数 args 须为 JSON 数组，例如 [] 或 [\"run\",\"mcp\"]");
        return;
      }
      let env: Record<string, string> = {};
      try {
        const parsed = JSON.parse(String(values.envText ?? "").trim() || "{}");
        if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
        env = Object.fromEntries(
          Object.entries(parsed as Record<string, unknown>).map(([k, v]) => [String(k), String(v)]),
        );
      } catch {
        message.error("环境变量 env 须为 JSON 对象，例如 {}");
        return;
      }
      if (enabled && !cmd) {
        message.error("启用 MCP 时必须填写 command");
        return;
      }
      const wasConfigured = Boolean(audioConfig.command?.trim());
      setAudioSaving(true);
      const payload: AudioPluginMcpConfig = {
        enabled,
        command: cmd,
        args,
        cwd: String(values.cwd ?? "").trim(),
        env,
      };
      const updated = await updateAudioPluginMcpConfig(payload);
      setAudioConfig(updated);
      audioForm.setFieldsValue({
        enabled: updated.enabled,
        command: updated.command,
        argsText: JSON.stringify(updated.args ?? []),
        cwd: updated.cwd,
        envText: JSON.stringify(updated.env ?? {}, null, 2),
      });
      if ((!wasConfigured || getPluginMode("audio") === "unused") && updated.command.trim()) {
        await ensureEnabledAfterBinding("audio");
      }
      message.success("音频 MCP 配置已保存");
    } catch {
      // 表单校验失败
    } finally {
      setAudioSaving(false);
    }
  };

  const handleTestAudioOutput = async () => {
    setAudioTesting(true);
    try {
      const res = await testAudioPluginOutput({ sample_rate: 16000, channels: 1 });
      if (res.success) {
        message.success(res.message || "测试音已下发");
      } else {
        message.warning(res.message || "测试失败");
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`测试失败: ${msg}`);
    } finally {
      setAudioTesting(false);
    }
  };

  const bindingMap = useMemo<Record<ConfigPluginKey, boolean>>(
    () => ({
      xiaomi: Boolean(bindingStatus?.is_bound),
      dida: Boolean(didaBindingStatus?.is_bound),
      wechat: false,
      openclaw: isStrictHttpUrl(openclawUrl),
      zeroclaw: isStrictHttpUrl(zeroclawUrl),
      camera: cameraConfig.source === "local" ? true : isStrictHttpUrl(cameraConfig.remote_url || ""),
      audio: Boolean(audioConfig.command?.trim()),
    }),
    [
      bindingStatus?.is_bound,
      didaBindingStatus?.is_bound,
      openclawUrl,
      zeroclawUrl,
      cameraConfig,
      audioConfig.command,
    ],
  );

  const catalogItems = useMemo(
    () =>
      ACCOUNT_SETTING_PLUGINS.map((plugin) => ({
        ...plugin,
        enabled: isPluginEnabled(plugin.key),
        bound: bindingMap[plugin.key],
        loading:
          catalogLoading ||
          (plugin.key === "xiaomi" && xiaomiLoading) ||
          (plugin.key === "dida" && didaLoading) ||
          (plugin.key === "audio" && (audioSaving || audioTesting)) ||
          modeUpdatingKey === plugin.key,
      })),
    [bindingMap, audioSaving, audioTesting, catalogLoading, didaLoading, modeUpdatingKey, pluginModes, xiaomiLoading],
  );

  const enabledItems = useMemo(() => catalogItems.filter((item) => item.enabled), [catalogItems]);
  const disabledItems = useMemo(() => catalogItems.filter((item) => !item.enabled), [catalogItems]);

  const activePlugin =
    activeConfig ? ACCOUNT_SETTING_PLUGINS.find((plugin) => plugin.key === activeConfig) ?? null : null;

  const renderPluginSwitch = (pluginKey: ConfigPluginKey) => (
    <div className="status-row">
      <Text strong>插件开启：</Text>
      <Switch
        checked={isPluginEnabled(pluginKey)}
        loading={modeUpdatingKey === pluginKey}
        onChange={(checked) => void setPluginEnable(pluginKey, checked)}
      />
      <Tag color={isPluginEnabled(pluginKey) ? "success" : "default"}>
        {isPluginEnabled(pluginKey) ? "已开启" : "未开启"}
      </Tag>
    </div>
  );

  const renderXiaomiDetail = () => (
    <Spin spinning={xiaomiLoading}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        {renderPluginSwitch("xiaomi")}
        <div className="status-row">
          <Text strong>绑定状态：</Text>
          {bindingMap.xiaomi ? (
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
            </div>
          </>
        )}

        {!bindingStatus?.is_bound && (
          <Button type="primary" icon={<LinkOutlined />} block onClick={handleBindXiaomi}>
            去绑定小米账号
          </Button>
        )}
      </Space>
    </Spin>
  );

  const renderDidaDetail = () => (
    <Spin spinning={didaLoading}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        {renderPluginSwitch("dida")}
        <div className="status-row">
          <Text strong>绑定状态：</Text>
          {bindingMap.dida ? (
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
              <Text strong>滴答账号：</Text>
              <Text>{didaBindingStatus.username}</Text>
            </div>
            {didaBindingStatus.bound_at && (
              <div className="status-row">
                <Text strong>绑定时间：</Text>
                <Text type="secondary">{new Date(didaBindingStatus.bound_at).toLocaleString("zh-CN")}</Text>
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
            </div>
          </>
        )}

        {!didaBindingStatus?.is_bound && (
          <Button type="primary" icon={<LinkOutlined />} block onClick={handleBindDida}>
            去绑定滴答清单
          </Button>
        )}
      </Space>
    </Spin>
  );

  const renderOpenClawDetail = () => (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {renderPluginSwitch("openclaw")}
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        绑定地址后默认开启，可随时关闭但保留绑定。
      </Paragraph>
      <Form form={openClawForm} layout="vertical">
        <Form.Item
          name="openclawUrl"
          label="OpenClaw 页面地址"
          rules={[
            {
              validator: async (_, value: string) => {
                const next = String(value ?? "").trim();
                if (!next) return;
                if (!isValidEmbedUrl(next)) throw new Error("请输入合法 URL");
              },
            },
          ]}
        >
          <Input allowClear placeholder="例如 https://openclaw.example.com" />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={() => void handleSaveOpenClaw()}>
              保存并绑定
            </Button>
            <Button
              danger
              onClick={() => {
                openClawForm.setFieldsValue({ openclawUrl: "" });
                void handleSaveOpenClaw();
              }}
            >
              解除绑定
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Space>
  );

  const renderZeroClawDetail = () => (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {renderPluginSwitch("zeroclaw")}
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        绑定地址后默认开启，可随时关闭但保留绑定。
      </Paragraph>
      <Form form={zeroClawForm} layout="vertical">
        <Form.Item
          name="zeroclawUrl"
          label="ZeroClaw 页面地址"
          rules={[
            {
              validator: async (_, value: string) => {
                const next = String(value ?? "").trim();
                if (!next) return;
                if (!isValidEmbedUrl(next)) throw new Error("请输入合法 URL");
              },
            },
          ]}
        >
          <Input allowClear placeholder="例如 https://zeroclaw.example.com" />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={() => void handleSaveZeroClaw()}>
              保存并绑定
            </Button>
            <Button
              danger
              onClick={() => {
                zeroClawForm.setFieldsValue({ zeroclawUrl: "" });
                void handleSaveZeroClaw();
              }}
            >
              解除绑定
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Space>
  );

  const renderCameraDetail = () => (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {renderPluginSwitch("camera")}
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        支持本地摄像头和远程摄像头。保存配置后默认开启，后续可关闭但保留绑定。
      </Paragraph>
      <Form form={cameraForm} layout="vertical" initialValues={cameraConfig}>
        <Form.Item label="摄像头类型" name="source" rules={[{ required: true, message: "请选择摄像头类型" }]}>
          <Select
            options={[
              { label: "本地摄像头", value: "local" },
              { label: "远程摄像头", value: "remote" },
            ]}
          />
        </Form.Item>

        {effectiveCameraSource === "local" ? (
          <Form.Item label="本地摄像头索引" name="local_index">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
        ) : (
          <Form.Item
            label="远程摄像头地址"
            name="remote_url"
            rules={[
              { required: true, message: "请输入远程摄像头地址" },
              {
                validator: async (_, value: string) => {
                  if (!isStrictHttpUrl(value || "")) throw new Error("请输入有效的 http/https URL");
                },
              },
            ]}
          >
            <Input placeholder="例如 https://camera.example.com/live" />
          </Form.Item>
        )}

        <Form.Item>
          <Button type="primary" loading={cameraSaving} onClick={() => void handleSaveCameraConfig()}>
            保存摄像头配置
          </Button>
        </Form.Item>
      </Form>
    </Space>
  );

  const renderWechatDetail = () => (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {renderPluginSwitch("wechat")}
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        微信能力由 MCP 网关代理下游 wechat 服务提供；请确保已启动网关且微信 MCP 进程可用。
      </Paragraph>
    </Space>
  );

  const renderAudioDetail = () => (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        stdio 参数与 Cursor MCP 一致，保存即写入服务端；未保存时可回退 <Text code>config.yaml</Text>。开启插件后在 Agent 配置中勾选「音频」。
      </Paragraph>
      {renderPluginSwitch("audio")}
      <Form form={audioForm} layout="vertical" style={{ maxWidth: 640 }}>
        <Form.Item label="启用 MCP 进程" name="enabled" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item
          label="command"
          name="command"
          rules={[{ required: false, message: "填写可执行文件或解释器路径" }]}
        >
          <Input allowClear placeholder='例如 uv 或 npx 或 C:\\path\\python.exe' />
        </Form.Item>
        <Form.Item
          label="args（JSON 数组）"
          name="argsText"
          rules={[{ required: true, message: "填写 JSON 数组" }]}
        >
          <Input.TextArea
            rows={3}
            placeholder='例如 ["run","mcp","esp32"] 或 []'
            style={{ fontFamily: "monospace" }}
          />
        </Form.Item>
        <Form.Item label="工作目录 cwd" name="cwd">
          <Input allowClear placeholder="可选，MCP 进程启动时的 cwd" />
        </Form.Item>
        <Form.Item
          label="环境变量 env（JSON 对象）"
          name="envText"
          rules={[{ required: true, message: "填写 JSON 对象" }]}
        >
          <Input.TextArea
            rows={4}
            placeholder='例如 {"KEY":"value"}'
            style={{ fontFamily: "monospace" }}
          />
        </Form.Item>
        <Form.Item>
          <Space wrap>
            <Button type="primary" loading={audioSaving} onClick={() => void handleSaveAudioMcpConfig()}>
              保存 MCP 配置
            </Button>
            <Button loading={audioTesting} onClick={() => void handleTestAudioOutput()}>
              测试扬声器输出
            </Button>
          </Space>
        </Form.Item>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          测试基于<strong>已保存</strong>配置；请先保存，并确保本机可启动该 MCP。
        </Paragraph>
      </Form>
    </Space>
  );

  const renderActiveConfigDetail = () => {
    if (activeConfig === "xiaomi") return renderXiaomiDetail();
    if (activeConfig === "dida") return renderDidaDetail();
    if (activeConfig === "openclaw") return renderOpenClawDetail();
    if (activeConfig === "zeroclaw") return renderZeroClawDetail();
    if (activeConfig === "camera") return renderCameraDetail();
    if (activeConfig === "wechat") return renderWechatDetail();
    if (activeConfig === "audio") return renderAudioDetail();
    return null;
  };

  const renderCatalogGroup = (items: typeof catalogItems, emptyText: string) => {
    if (items.length === 0) {
      return (
        <div className="plugin-section-empty">
          <Text type="secondary">{emptyText}</Text>
        </div>
      );
    }

    return (
      <Row gutter={[16, 16]}>
        {items.map((item) => (
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
                      <Space size={4} wrap>
                        <Tag color={item.enabled ? "success" : "default"} className="config-tile-tag">
                          {item.enabled ? "已开启" : "未开启"}
                        </Tag>
                        <Tag
                          icon={item.bound ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                          color={item.bound ? "blue" : "default"}
                          className="config-tile-tag"
                        >
                          {item.key === "audio" ? (item.bound ? "已配置" : "未配置") : item.bound ? "已绑定" : "未绑定"}
                        </Tag>
                      </Space>
                    </div>
                    <Paragraph
                      type="secondary"
                      className="config-tile-desc"
                      ellipsis={{ rows: 2 }}
                      style={{ marginBottom: 0 }}
                    >
                      {item.blurb}
                    </Paragraph>
                  </div>
                  <RightOutlined className="config-tile-chevron" aria-hidden />
                </div>
              </Spin>
            </button>
          </Col>
        ))}
      </Row>
    );
  };

  return (
    <>
      <Card className="config-catalog-card" bordered={false}>
        <Paragraph type="secondary" className="config-catalog-intro">
          插件卡片按“开启/未开启”分组；绑定状态独立显示。点击卡片可管理开启开关和绑定配置。
        </Paragraph>

        <div className="plugin-section">
          <div className="plugin-section-title-row">
            <Text strong>已开启插件</Text>
            <Tag color="success">{enabledItems.length}</Tag>
          </div>
          {renderCatalogGroup(enabledItems, "当前没有已开启插件")}
        </div>

        <div className="plugin-section-divider" aria-hidden />

        <div className="plugin-section">
          <div className="plugin-section-title-row">
            <Text strong>未开启插件</Text>
            <Tag>{disabledItems.length}</Tag>
          </div>
          {renderCatalogGroup(disabledItems, "当前没有未开启插件")}
        </div>
      </Card>

      <Drawer
        title={activePlugin?.title ?? ""}
        placement="right"
        width={Math.min(560, typeof window !== "undefined" ? window.innerWidth - 24 : 560)}
        open={activeConfig !== null}
        onClose={() => setActiveConfig(null)}
        destroyOnClose
        className="config-detail-drawer"
      >
        {activeConfig ? renderActiveConfigDetail() : null}
      </Drawer>
    </>
  );
};

export default BindingSection;
