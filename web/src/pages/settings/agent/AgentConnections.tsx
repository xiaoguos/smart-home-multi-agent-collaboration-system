import {
  Button,
  Form,
  Input,
  InputNumber,
  Switch,
  message,
  Table,
  Modal,
  Tag,
} from "antd";
import React, { useState, useEffect } from "react";
import { EditOutlined } from "@ant-design/icons";
import "../styles/setting.sass";
import { getAgents, updateAgent, type Agent } from "../../../api/config";

const AgentConnections: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selected, setSelected] = useState<Agent | null>(null);
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setAgents(await getAgents());
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

  const openEdit = (agent: Agent) => {
    setSelected(agent);
    form.setFieldsValue(agent);
    setModalOpen(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      if (selected) {
        await updateAgent(selected.id, values);
        message.success("Agent 连接信息已更新");
      }
      setModalOpen(false);
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
    }
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
      title: "操作",
      key: "action",
      render: (_: unknown, record: Agent) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          编辑
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">连接与状态</h2>
        <p className="setting-page-desc">配置各 Agent 的主机、端口与启用状态</p>
      </div>
      <Table dataSource={agents} columns={columns} rowKey="id" loading={loading} pagination={false} />

      <Modal title="编辑 Agent 连接信息" open={modalOpen} onOk={() => void save()} onCancel={() => setModalOpen(false)} width={500}>
        <Form form={form} layout="vertical">
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
          <Form.Item label="启用" name="is_enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AgentConnections;
