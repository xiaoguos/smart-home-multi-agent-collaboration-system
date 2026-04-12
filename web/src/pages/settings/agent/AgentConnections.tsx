import {
  Button,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  Checkbox,
  message,
  Table,
  Modal,
  Tag,
  Space,
  Typography,
  Popover,
} from "antd";
import React, { useState, useEffect } from "react";
import {
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  PoweroffOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import "../styles/setting.sass";
import {
  createAgent,
  deleteAgent,
  getAgentDeviceBindings,
  getAgentRuntime,
  getAgents,
  getDevices,
  updateAgent,
  getAgentPrompt,
  updateAgentPrompt,
  getAIModels,
  replaceAgentDeviceBindings,
  syncAgentDeviceOfflinePolicy,
  startAgentRuntime,
  stopAgentRuntime,
  updateAgentModelBinding,
  getLocalIpv4,
  getAgentPluginsBundle,
  replaceAgentPlugins,
  syncAgentRuntimesWithConfig,
  type AgentPluginCatalogItem,
  type AgentCreate,
  type AgentDeviceBinding,
  type AIModel,
  type Agent,
  type Device,
} from "../../../api/config";
import { getXiaomiDevices, type XiaomiDevice } from "../../../api/xiaomi";

const { Text } = Typography;

const AgentConnections: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [deviceLoading, setDeviceLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [customDevices, setCustomDevices] = useState<Device[]>([]);
  const [xiaomiDevices, setXiaomiDevices] = useState<XiaomiDevice[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<Agent | null>(null);
  const [selectedPromptAgent, setSelectedPromptAgent] = useState<Agent | null>(null);
  const [selectedDeviceAgent, setSelectedDeviceAgent] = useState<Agent | null>(null);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [promptModalOpen, setPromptModalOpen] = useState(false);
  const [deviceModalOpen, setDeviceModalOpen] = useState(false);
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [connectionForm] = Form.useForm();
  const [promptForm] = Form.useForm();
  const [deviceForm] = Form.useForm();
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [activeModels, setActiveModels] = useState<AIModel[]>([]);
  const [lanIpv4, setLanIpv4] = useState<string>("");
  const [pluginCatalog, setPluginCatalog] = useState<AgentPluginCatalogItem[]>([]);

  const resolveUserId = (): number | null => {
    try {
      const raw = localStorage.getItem("user_info");
      if (!raw) return null;
      const user = JSON.parse(raw) as { id?: number };
      return typeof user.id === "number" ? user.id : null;
    } catch {
      return null;
    }
  };

  const load = async () => {
    try {
      setLoading(true);
      const userId = resolveUserId();
      if (userId) {
        try {
          await syncAgentDeviceOfflinePolicy(userId);
        } catch {
          // 米家 MCP 不可用时跳过自动禁用策略
        }
      }
      try {
        await syncAgentRuntimesWithConfig();
      } catch {
        // 与本地进程对齐失败时不阻断列表加载
      }
      const [data, models, activeCustomDevices] = await Promise.all([
        getAgents(),
        getAIModels(true),
        getDevices(undefined, true),
      ]);
      setAgents(data);
      setActiveModels(models);
      setCustomDevices(activeCustomDevices);

      const promptEntries = await Promise.all(
        data.map(async (agent) => {
          try {
            const prompt = await getAgentPrompt(agent.agent_code);
            return [agent.agent_code, prompt.prompt_text] as const;
          } catch {
            return [agent.agent_code, ""] as const;
          }
        }),
      );
      setPrompts(Object.fromEntries(promptEntries));
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`加载 Agent 失败: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    void getLocalIpv4()
      .then((r) => setLanIpv4(String(r?.ipv4 ?? "").trim()))
      .catch(() => setLanIpv4(""));
  }, []);

  const isLoopbackServiceHost = (h: string): boolean => {
    const n = String(h || "").trim().toLowerCase();
    return (
      !n ||
      n === "localhost" ||
      n === "0.0.0.0" ||
      n === "127.0.0.1" ||
      n === "::" ||
      n === "::1"
    );
  };

  const openConnectionCreate = () => {
    setCreatingAgent(true);
    setSelectedConnection(null);
    setPluginCatalog([]);
    connectionForm.resetFields();
    connectionForm.setFieldsValue({
      host: "127.0.0.1",
      port: 13000,
      is_enabled: true,
      model_id: undefined,
      runtime_command: "",
      runtime_cwd: "",
      plugin_keys: [],
    });
    setConnectionModalOpen(true);
  };

  const openConnectionEdit = async (agent: Agent) => {
    setCreatingAgent(false);
    setSelectedConnection(agent);
    connectionForm.setFieldsValue({
      ...agent,
      model_id: agent.model_id ?? undefined,
      runtime_command: "",
      runtime_cwd: "",
    });
    try {
      const runtime = await getAgentRuntime(agent.agent_code);
      connectionForm.setFieldsValue({
        runtime_command: runtime.command ?? "",
        runtime_cwd: runtime.cwd ?? "",
      });
    } catch {
      // 忽略运行时读取失败，允许用户手动填写
    }
    try {
      const bundle = await getAgentPluginsBundle(agent.agent_code);
      setPluginCatalog(bundle.catalog);
      connectionForm.setFieldsValue({
        plugin_keys: bundle.catalog.filter((c) => c.selected).map((c) => c.plugin_key),
      });
    } catch {
      setPluginCatalog([]);
    }
    setConnectionModalOpen(true);
  };

  const saveConnection = async () => {
    try {
      const values = await connectionForm.validateFields();
      const { model_id, runtime_command, runtime_cwd, plugin_keys, ...agentValues } = values;

      if (creatingAgent) {
        const payload: AgentCreate = {
          ...agentValues,
          runtime_command: String(runtime_command || "").trim() || undefined,
          runtime_cwd: String(runtime_cwd || "").trim() || undefined,
        };
        await createAgent(payload);
        await updateAgentModelBinding(payload.agent_code, model_id ?? null);
        message.success("Agent 已创建并完成配置");
      } else if (selectedConnection) {
        await updateAgent(selectedConnection.id, {
          ...agentValues,
          runtime_command:
            runtime_command === undefined ? undefined : String(runtime_command || "").trim() || null,
          runtime_cwd: runtime_cwd === undefined ? undefined : String(runtime_cwd || "").trim() || null,
        });
        await updateAgentModelBinding(selectedConnection.agent_code, model_id ?? null);
        const keys = Array.isArray(plugin_keys) ? plugin_keys.map(String) : [];
        await replaceAgentPlugins(selectedConnection.agent_code, keys);
        message.success("Agent 配置与模型已更新");
      }
      setConnectionModalOpen(false);
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
    }
  };

  const openDeviceBinding = async (agent: Agent) => {
    setSelectedDeviceAgent(agent);
    setDeviceModalOpen(true);
    setDeviceLoading(true);
    try {
      const userId = resolveUserId();
      const [bindingsResp, xiaomiResp] = await Promise.all([
        getAgentDeviceBindings(agent.agent_code),
        userId ? getXiaomiDevices(userId) : Promise.resolve(null),
      ]);
      const xiaomiList = xiaomiResp?.result?.devices || [];
      setXiaomiDevices(xiaomiList);

      deviceForm.setFieldsValue({
        custom_device_ids: bindingsResp.bindings
          .filter((item) => item.source === "custom")
          .map((item) => item.device_id),
        xiaomi_device_ids: bindingsResp.bindings
          .filter((item) => item.source === "xiaomi")
          .map((item) => item.device_id),
      });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`加载设备绑定失败: ${msg}`);
    } finally {
      setDeviceLoading(false);
    }
  };

  const saveDeviceBinding = async () => {
    if (!selectedDeviceAgent) return;
    try {
      const values = await deviceForm.validateFields();
      const customIds: string[] = values.custom_device_ids || [];
      const xiaomiIds: string[] = values.xiaomi_device_ids || [];
      const customMap = new Map(customDevices.map((item) => [item.device_code, item]));
      const xiaomiMap = new Map(xiaomiDevices.map((item) => [item.did, item]));
      const bindings: AgentDeviceBinding[] = [];

      customIds.forEach((deviceId) => {
        const device = customMap.get(deviceId);
        if (!device) return;
        bindings.push({
          source: "custom",
          device_id: device.device_code,
          device_name: device.device_name,
          model: device.model,
        });
      });

      for (const deviceId of xiaomiIds) {
        const device = xiaomiMap.get(deviceId);
        if (!device) continue;
        if (!device.isOnline) {
          message.error(`米家设备「${device.name}」离线，无法绑定`);
          return;
        }
        bindings.push({
          source: "xiaomi",
          device_id: device.did,
          device_name: device.name,
          model: device.model,
        });
      }

      const uid = resolveUserId();
      if (bindings.some((b) => b.source === "xiaomi") && !uid) {
        message.error("绑定米家设备前请先登录系统账号");
        return;
      }

      await replaceAgentDeviceBindings(selectedDeviceAgent.agent_code, bindings, {
        systemUserId: uid ?? undefined,
      });
      message.success("设备绑定已更新");
      setDeviceModalOpen(false);
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存设备绑定失败: ${msg}`);
    }
  };

  const handleDeleteAgent = (agent: Agent) => {
    Modal.confirm({
      title: `确认删除 Agent「${agent.agent_name}」?`,
      content: "删除后将无法再对话，请确认已完成设备解绑。",
      okText: "确认删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await deleteAgent(agent.agent_code);
          message.success("Agent 已删除");
          void load();
        } catch (error: unknown) {
          const msg = error instanceof Error ? error.message : String(error);
          message.error(`删除失败: ${msg}`);
        }
      },
    });
  };

  const handleStartRuntime = async (agent: Agent) => {
    try {
      await startAgentRuntime(agent.agent_code);
      message.success("Agent 进程已启动");
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`启动失败: ${msg}`);
    }
  };

  const handleStopRuntime = async (agent: Agent) => {
    try {
      await stopAgentRuntime(agent.agent_code);
      message.success("Agent 进程已停止");
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`停止失败: ${msg}`);
    }
  };

  const openPromptEdit = (agent: Agent) => {
    setSelectedPromptAgent(agent);
    promptForm.setFieldsValue({ prompt_text: prompts[agent.agent_code] ?? "" });
    setPromptModalOpen(true);
  };

  const savePrompt = async () => {
    try {
      const values = await promptForm.validateFields();
      if (selectedPromptAgent) {
        await updateAgentPrompt(selectedPromptAgent.agent_code, values.prompt_text);
        setPrompts((prev) => ({
          ...prev,
          [selectedPromptAgent.agent_code]: values.prompt_text,
        }));
        message.success("Agent 系统提示词已更新");
      }
      setPromptModalOpen(false);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
    }
  };

  const renderPromptPreview = (agentCode: string) => {
    const text = prompts[agentCode] ?? "";
    if (!text) return "（空）";
    const cellMax = 28;
    const popoverMax = 280;
    const short = text.length > cellMax ? `${text.slice(0, cellMax)}…` : text;
    if (text.length <= cellMax) return short;
    const popoverText =
      text.length > popoverMax ? `${text.slice(0, popoverMax)}…` : text;
    return (
      <Popover
        trigger="hover"
        placement="leftTop"
        mouseEnterDelay={0.35}
        styles={{
          body: {
            maxWidth: 320,
            maxHeight: 200,
            padding: "10px 12px",
            overflow: "auto",
            fontSize: 12,
            lineHeight: 1.55,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          },
        }}
        content={
          <>
            {popoverText}
            {text.length > popoverMax ? (
              <span style={{ display: "block", marginTop: 8, color: "rgba(0,0,0,0.45)" }}>
                全文请在「提示词」中编辑查看
              </span>
            ) : null}
          </>
        }
      >
        <span style={{ cursor: "default" }}>{short}</span>
      </Popover>
    );
  };

  const columns = [
    { title: "名称", dataIndex: "agent_name", key: "agent_name" },
    {
      title: "主机",
      dataIndex: "host",
      key: "host",
      render: (host: string) => {
        const normalized = String(host || "").trim().toLowerCase();
        if (!normalized || normalized === "localhost") return "127.0.0.1";
        if (normalized === "0.0.0.0") return "127.0.0.1";
        return host;
      },
    },
    { title: "端口", dataIndex: "port", key: "port" },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      render: (desc?: string) => {
        const text = String(desc || "").trim();
        if (!text) return "—";
        const cellMax = 22;
        const popoverMax = 160;
        const short = text.length > cellMax ? `${text.slice(0, cellMax)}…` : text;
        if (text.length <= cellMax) return short;
        const popoverText =
          text.length > popoverMax ? `${text.slice(0, popoverMax)}…` : text;
        return (
          <Popover
            trigger="hover"
            placement="leftTop"
            mouseEnterDelay={0.35}
            styles={{
              body: {
                maxWidth: 280,
                maxHeight: 140,
                padding: "10px 12px",
                overflow: "auto",
                fontSize: 12,
                lineHeight: 1.55,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              },
            }}
            content={
              <>
                {popoverText}
                {text.length > popoverMax ? (
                  <span style={{ display: "block", marginTop: 6, color: "rgba(0,0,0,0.45)" }}>
                    更多请在编辑中查看
                  </span>
                ) : null}
              </>
            }
          >
            <span style={{ cursor: "default" }}>{short}</span>
          </Popover>
        );
      },
    },
    {
      title: "状态",
      dataIndex: "is_enabled",
      key: "is_enabled",
      render: (val: boolean) => (val ? <Tag color="green">启用</Tag> : <Tag color="red">禁用</Tag>),
    },
    {
      title: "运行状态",
      key: "runtime_status",
      render: (_: unknown, record: Agent) => {
        const runtimeStatus = (record.runtime_status || "stopped").toLowerCase();
        if (runtimeStatus === "running") {
          return <Tag color="success">运行中 PID:{record.runtime_pid || "-"}</Tag>;
        }
        if (runtimeStatus === "starting") {
          return <Tag color="processing">启动中 PID:{record.runtime_pid || "-"}</Tag>;
        }
        return <Tag>已停止</Tag>;
      },
    },
    {
      title: "服务地址",
      key: "runtime_addr",
      render: (_: unknown, record: Agent) => {
        const rawHost = String(record.runtime_server_ip || record.host || "").trim();
        const displayHost = isLoopbackServiceHost(rawHost)
          ? lanIpv4 || "127.0.0.1"
          : rawHost;
        return <Text code>{`${displayHost}:${record.runtime_port || record.port}`}</Text>;
      },
    },
    {
      title: "绑定模型",
      key: "model_name",
      render: (_: unknown, record: Agent) =>
        record.model_name ? <Tag color="blue">{record.model_name}</Tag> : <Tag>跟随默认模型</Tag>,
    },
    {
      title: "提示词预览",
      key: "prompt_preview",
      render: (_: unknown, record: Agent) => (
        <div style={{ maxWidth: 520, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {renderPromptPreview(record.agent_code)}
        </div>
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 380,
      render: (_: unknown, record: Agent) => {
        const runtimeStatus = (record.runtime_status || "stopped").toLowerCase();
        const isRuntimeUp = runtimeStatus === "running" || runtimeStatus === "starting";
        return (
        <Space size={[4, 4]} wrap>
          <Button type="link" icon={<SettingOutlined />} onClick={() => void openConnectionEdit(record)}>
            状态/连接
          </Button>
          {isRuntimeUp ? (
            <Button type="link" icon={<PoweroffOutlined />} onClick={() => void handleStopRuntime(record)}>
              停止
            </Button>
          ) : (
            <Button type="link" icon={<PlayCircleOutlined />} onClick={() => void handleStartRuntime(record)}>
              启动
            </Button>
          )}
          <Button type="link" onClick={() => void openDeviceBinding(record)}>
            设备绑定
          </Button>
          <Button type="link" icon={<EditOutlined />} onClick={() => openPromptEdit(record)}>
            提示词
          </Button>
          <Button
            type="link"
            danger
            disabled={record.agent_code === "conductor"}
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteAgent(record)}
          >
            删除
          </Button>
        </Space>
        );
      },
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">Agent配置</h2>
        <p className="setting-page-desc">整合管理 Agent 生命周期、系统提示词、设备绑定与模型绑定</p>
      </div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openConnectionCreate}>
          新增Agent
        </Button>
      </Space>
      <Table
        dataSource={agents}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        scroll={{ x: 1600 }}
      />

      <Modal
        title={creatingAgent ? "新增 Agent" : "编辑 Agent 状态与连接"}
        open={connectionModalOpen}
        onOk={() => void saveConnection()}
        onCancel={() => setConnectionModalOpen(false)}
        width={640}
      >
        <Form form={connectionForm} layout="vertical">
          {creatingAgent ? (
            <Form.Item
              label="Agent代码"
              name="agent_code"
              rules={[
                { required: true, message: "请输入Agent代码" },
                { pattern: /^[a-z0-9_]+$/, message: "仅支持小写字母、数字与下划线" },
              ]}
            >
              <Input placeholder="例如 weather_assistant" />
            </Form.Item>
          ) : null}
          <Form.Item label="Agent名称" name="agent_name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="主机" name="host">
            <Input />
          </Form.Item>
          <Form.Item label="端口" name="port" rules={[{ required: true }]}>
            <InputNumber min={1} max={65535} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="绑定模型"
            name="model_id"
            extra="不选择时将跟随全局默认模型"
          >
            <Select
              allowClear
              placeholder="跟随默认模型"
              options={activeModels.map((item) => ({
                value: item.id,
                label: `${item.model_name} (${item.provider})`,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="本地启动命令（可选）"
            name="runtime_command"
            extra="留空时自动按 agents/<agent_code>_agent 执行 uv run ."
          >
            <Input placeholder="例如 uv run . --host 127.0.0.1 --port 12005" />
          </Form.Item>
          <Form.Item
            label="本地启动目录（可选）"
            name="runtime_cwd"
            extra="相对路径基于项目根目录，也可填绝对路径"
          >
            <Input placeholder="例如 agents/weather_assistant_agent" />
          </Form.Item>
          {!creatingAgent && pluginCatalog.length > 0 ? (
            <Form.Item
              label="可用插件"
              name="plugin_keys"
              extra="仅可为「插件扩展」中已开启的插件分配能力；保存后主 Agent 等进程将按此加载工具与说明。"
            >
              <Checkbox.Group
                style={{ width: "100%" }}
                options={pluginCatalog.map((c) => ({
                  value: c.plugin_key,
                  label: `${c.title}（${c.mode}）${c.description ? ` — ${c.description}` : ""}`,
                  disabled: !c.allow_assign,
                }))}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="启用" name="is_enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`编辑系统提示词 — ${selectedPromptAgent?.agent_name ?? ""}`}
        open={promptModalOpen}
        onOk={() => void savePrompt()}
        onCancel={() => setPromptModalOpen(false)}
        width={900}
      >
        <Form form={promptForm} layout="vertical">
          <Form.Item
            label="系统提示词"
            name="prompt_text"
            rules={[{ required: true, message: "请输入系统提示词" }]}
          >
            <Input.TextArea rows={18} style={{ fontFamily: "monospace" }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`设备绑定 — ${selectedDeviceAgent?.agent_name ?? ""}`}
        open={deviceModalOpen}
        onOk={() => void saveDeviceBinding()}
        onCancel={() => setDeviceModalOpen(false)}
        confirmLoading={deviceLoading}
        width={760}
      >
        <Form form={deviceForm} layout="vertical">
          <Form.Item label="自定义设备" name="custom_device_ids">
            <Select
              mode="multiple"
              allowClear
              placeholder="选择要绑定的自定义设备"
              options={customDevices.map((item) => ({
                value: item.device_code,
                label: `${item.device_name} (${item.device_code})`,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="米家设备"
            name="xiaomi_device_ids"
            extra="仅可选择当前在线的米家设备；若已绑设备全部离线，系统将自动禁用该 Agent"
          >
            <Select
              mode="multiple"
              allowClear
              placeholder="选择要绑定的米家设备（离线项不可选）"
              options={xiaomiDevices.map((item) => ({
                value: item.did,
                label: `${item.name} (${item.model})${item.isOnline ? "" : " [离线]"}`,
                disabled: !item.isOnline,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AgentConnections;
