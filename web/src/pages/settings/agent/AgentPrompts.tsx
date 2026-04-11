import {
  Button,
  Form,
  Input,
  message,
  Table,
  Modal,
  Tag,
} from "antd";
import React, { useState, useEffect } from "react";
import { EditOutlined } from "@ant-design/icons";
import "../styles/setting.sass";
import {
  getAgents,
  getAgentPrompt,
  updateAgentPrompt,
  type Agent,
} from "../../../api/config";

const AgentPrompts: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [promptAgent, setPromptAgent] = useState<Agent | null>(null);
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const data = await getAgents();
      setAgents(data);
      const map: Record<string, string> = {};
      for (const agent of data) {
        try {
          const p = await getAgentPrompt(agent.agent_code);
          map[agent.agent_code] = p.prompt_text;
        } catch {
          map[agent.agent_code] = "";
        }
      }
      setPrompts(map);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`加载失败: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openEdit = (agent: Agent) => {
    setPromptAgent(agent);
    form.setFieldsValue({ prompt_text: prompts[agent.agent_code] ?? "" });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      if (promptAgent) {
        await updateAgentPrompt(promptAgent.agent_code, values.prompt_text);
        message.success("系统提示词已更新");
        setPrompts((prev) => ({ ...prev, [promptAgent.agent_code]: values.prompt_text }));
      }
      setModalOpen(false);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
    }
  };

  const columns = [
    { title: "Agent 名称", dataIndex: "agent_name", key: "agent_name", width: 160 },
    { title: "代码", dataIndex: "agent_code", key: "agent_code", width: 140 },
    {
      title: "状态",
      dataIndex: "is_enabled",
      key: "is_enabled",
      width: 90,
      render: (val: boolean) => (val ? <Tag color="green">启用</Tag> : <Tag color="red">禁用</Tag>),
    },
    {
      title: "提示词预览",
      key: "preview",
      render: (_: unknown, record: Agent) => {
        const t = prompts[record.agent_code] ?? "";
        const show = t.length > 120 ? `${t.slice(0, 120)}…` : t || "（空）";
        return <div style={{ maxWidth: 480, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{show}</div>;
      },
    },
    {
      title: "操作",
      key: "action",
      width: 120,
      render: (_: unknown, record: Agent) => (
        <Button type="primary" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          编辑
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">系统提示词</h2>
        <p className="setting-page-desc">按 Agent 维护系统 Prompt，修改后需重启对应 Agent 服务</p>
      </div>
      <Table
        dataSource={agents}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        scroll={{ x: 900 }}
      />

      <Modal
        title={`编辑提示词 — ${promptAgent?.agent_name ?? ""}`}
        open={modalOpen}
        onOk={() => void save()}
        onCancel={() => setModalOpen(false)}
        width={900}
        okText="保存"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="系统提示词" name="prompt_text" rules={[{ required: true, message: "请输入内容" }]}>
            <Input.TextArea rows={18} style={{ fontFamily: "monospace" }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AgentPrompts;
