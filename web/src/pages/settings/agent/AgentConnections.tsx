import {
  Button,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  message,
  Table,
  Modal,
  Tag,
  Space,
} from "antd";
import React, { useState, useEffect } from "react";
import { EditOutlined, SettingOutlined } from "@ant-design/icons";
import "../styles/setting.sass";
import {
  getAgents,
  updateAgent,
  getAgentPrompt,
  updateAgentPrompt,
  getAIModels,
  updateAgentModelBinding,
  type AIModel,
  type Agent,
} from "../../../api/config";

const AgentConnections: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<Agent | null>(null);
  const [selectedPromptAgent, setSelectedPromptAgent] = useState<Agent | null>(null);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [promptModalOpen, setPromptModalOpen] = useState(false);
  const [connectionForm] = Form.useForm();
  const [promptForm] = Form.useForm();
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [activeModels, setActiveModels] = useState<AIModel[]>([]);

  const load = async () => {
    try {
      setLoading(true);
      const [data, models] = await Promise.all([getAgents(), getAIModels(true)]);
      setAgents(data);
      setActiveModels(models);

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

  const openConnectionEdit = (agent: Agent) => {
    setSelectedConnection(agent);
    connectionForm.setFieldsValue({
      ...agent,
      model_id: agent.model_id ?? undefined,
    });
    setConnectionModalOpen(true);
  };

  const saveConnection = async () => {
    try {
      const values = await connectionForm.validateFields();
      if (selectedConnection) {
        const { model_id, ...agentValues } = values;
        await updateAgent(selectedConnection.id, agentValues);
        await updateAgentModelBinding(selectedConnection.agent_code, model_id ?? null);
        message.success("Agent 配置与模型已更新");
      }
      setConnectionModalOpen(false);
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
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
    return text.length > 120 ? `${text.slice(0, 120)}…` : text;
  };

  const columns = [
    { title: "名称", dataIndex: "agent_name", key: "agent_name" },
    { title: "代码", dataIndex: "agent_code", key: "agent_code" },
    { title: "主机", dataIndex: "host", key: "host" },
    { title: "端口", dataIndex: "port", key: "port" },
    { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
    {
      title: "状态",
      dataIndex: "is_enabled",
      key: "is_enabled",
      render: (val: boolean) => (val ? <Tag color="green">启用</Tag> : <Tag color="red">禁用</Tag>),
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
      width: 180,
      render: (_: unknown, record: Agent) => (
        <Space size={4}>
          <Button type="link" icon={<SettingOutlined />} onClick={() => openConnectionEdit(record)}>
            状态/连接
          </Button>
          <Button type="link" icon={<EditOutlined />} onClick={() => openPromptEdit(record)}>
            提示词
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">Agent配置</h2>
        <p className="setting-page-desc">整合管理 Agent 连接状态、系统提示词与模型绑定</p>
      </div>
      <Table
        dataSource={agents}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        scroll={{ x: 1000 }}
      />

      <Modal
        title="编辑 Agent 状态与连接"
        open={connectionModalOpen}
        onOk={() => void saveConnection()}
        onCancel={() => setConnectionModalOpen(false)}
        width={500}
      >
        <Form form={connectionForm} layout="vertical">
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
    </>
  );
};

export default AgentConnections;
