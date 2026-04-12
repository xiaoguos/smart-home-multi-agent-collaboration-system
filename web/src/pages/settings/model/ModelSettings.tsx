import {
  Button,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
  Table,
  Modal,
  Space,
  Tag,
} from "antd";
import React, { useState, useEffect } from "react";
import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import "../styles/setting.sass";
import {
  getAIModels,
  updateAIModel,
  createAIModel,
  type AIModel,
} from "../../../api/config";

const ModelSettings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [aiModels, setAiModels] = useState<AIModel[]>([]);
  const [selected, setSelected] = useState<AIModel | null>(null);
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setAiModels(await getAIModels());
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`加载AI模型配置失败: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openEdit = (model: AIModel) => {
    setSelected(model);
    setCreating(false);
    form.setFieldsValue(model);
    setModalOpen(true);
  };

  const openCreate = () => {
    setSelected(null);
    setCreating(true);
    form.resetFields();
    form.setFieldsValue({
      temperature: 0.7,
      max_tokens: 2048,
      model_type: "chat",
      is_default: false,
      is_active: true,
    });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      if (creating) {
        await createAIModel(values);
        message.success("AI模型创建成功");
      } else if (selected) {
        await updateAIModel(selected.id, values);
        message.success("AI模型更新成功");
      }
      setModalOpen(false);
      void load();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
    }
  };

  const columns = [
    {
      title: "模型名称",
      dataIndex: "model_name",
      key: "model_name",
      render: (value: string, record: AIModel) => (
        <Space size={8}>
          <span>{value}</span>
          {record.is_default ? <Tag color="blue">默认</Tag> : null}
        </Space>
      ),
    },
    { title: "提供商", dataIndex: "provider", key: "provider" },
    { title: "API Base", dataIndex: "api_base", key: "api_base", ellipsis: true },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (val: boolean) => (val ? "启用" : "禁用"),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: AIModel) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          编辑
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">LLM 模型</h2>
        <p className="setting-page-desc">管理对话使用的 LLM 与 API 凭据</p>
      </div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增模型
        </Button>
      </Space>
      <Table
        dataSource={aiModels}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={creating ? "新增 AI 模型" : "编辑 AI 模型"}
        open={modalOpen}
        onOk={() => void save()}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="模型名称" name="model_name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="提供商" name="provider" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="deepseek">DeepSeek</Select.Option>
              <Select.Option value="openai">OpenAI</Select.Option>
              <Select.Option value="baidu">百度</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="API Key" name="api_key" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item label="API Base URL" name="api_base" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="温度参数" name="temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="最大Token数" name="max_tokens">
            <InputNumber min={1} max={8192} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="设为默认" name="is_default" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ModelSettings;
