import {
  Button,
  Form,
  Input,
  Select,
  Tabs,
  Card,
  Switch,
  InputNumber,
  message,
  Table,
  Modal,
  Space,
} from "antd";
import React, { useState, useEffect } from "react";
import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import "./style/setting.sass";
import {
  getAIModels,
  updateAIModel,
  createAIModel,
  getAgents,
  updateAgent,
  getDevices,
  updateDevice,
  createDevice,
  type AIModel,
  type Agent,
  type Device,
} from "../api/config";

const Setting: React.FC = () => {
  const [activeTab, setActiveTab] = useState("1");
  
  // 各表格的loading状态
  const [aiModelLoading, setAiModelLoading] = useState(false);
  const [agentLoading, setAgentLoading] = useState(false);
  const [deviceLoading, setDeviceLoading] = useState(false);

  // AI模型配置状态
  const [aiModels, setAiModels] = useState<AIModel[]>([]);
  const [selectedAIModel, setSelectedAIModel] = useState<AIModel | null>(null);
  const [aiModelForm] = Form.useForm();
  const [isAIModelModalVisible, setIsAIModelModalVisible] = useState(false);
  const [isCreatingAIModel, setIsCreatingAIModel] = useState(false);

  // Agent配置状态
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [agentForm] = Form.useForm();
  const [isAgentModalVisible, setIsAgentModalVisible] = useState(false);

  // 设备配置状态
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [deviceForm] = Form.useForm();
  const [isDeviceModalVisible, setIsDeviceModalVisible] = useState(false);
  const [isCreatingDevice, setIsCreatingDevice] = useState(false);

  // ==================== 数据加载 ====================

  const loadAIModels = async () => {
    try {
      setAiModelLoading(true);
      const data = await getAIModels();
      setAiModels(data);
    } catch (error: any) {
      message.error(`加载AI模型配置失败: ${error.message}`);
    } finally {
      setAiModelLoading(false);
    }
  };

  const loadAgents = async () => {
    try {
      setAgentLoading(true);
      const data = await getAgents();
      setAgents(data);
    } catch (error: any) {
      message.error(`加载Agent配置失败: ${error.message}`);
    } finally {
      setAgentLoading(false);
    }
  };

  const loadDevices = async () => {
    try {
      setDeviceLoading(true);
      const data = await getDevices();
      setDevices(data);
    } catch (error: any) {
      message.error(`加载设备配置失败: ${error.message}`);
    } finally {
      setDeviceLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "1") loadAIModels();
    else if (activeTab === "2") loadAgents();
    else if (activeTab === "3") loadDevices();
  }, [activeTab]);

  // ==================== AI模型管理 ====================

  const handleEditAIModel = (model: AIModel) => {
    setSelectedAIModel(model);
    setIsCreatingAIModel(false);
    aiModelForm.setFieldsValue(model);
    setIsAIModelModalVisible(true);
  };

  const handleCreateAIModel = () => {
    setSelectedAIModel(null);
    setIsCreatingAIModel(true);
    aiModelForm.resetFields();
    aiModelForm.setFieldsValue({
      temperature: 0.7,
      max_tokens: 2048,
      model_type: "chat",
      is_default: false,
      is_active: true,
    });
    setIsAIModelModalVisible(true);
  };

  const handleSaveAIModel = async () => {
    try {
      const values = await aiModelForm.validateFields();

      if (isCreatingAIModel) {
        await createAIModel(values);
        message.success("AI模型创建成功");
      } else if (selectedAIModel) {
        await updateAIModel(selectedAIModel.id, values);
        message.success("AI模型更新成功");
      }

      setIsAIModelModalVisible(false);
      loadAIModels();
    } catch (error: any) {
      message.error(`保存失败: ${error.message}`);
    }
  };

  // ==================== Agent管理 ====================

  const handleEditAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    agentForm.setFieldsValue(agent);
    setIsAgentModalVisible(true);
  };

  const handleSaveAgent = async () => {
    try {
      const values = await agentForm.validateFields();

      if (selectedAgent) {
        await updateAgent(selectedAgent.id, values);
        message.success("Agent配置更新成功");
      }

      setIsAgentModalVisible(false);
      loadAgents();
    } catch (error: any) {
      message.error(`保存失败: ${error.message}`);
    }
  };

  // ==================== 设备管理 ====================

  const handleEditDevice = (device: Device) => {
    setSelectedDevice(device);
    setIsCreatingDevice(false);
    deviceForm.setFieldsValue(device);
    setIsDeviceModalVisible(true);
  };

  const handleCreateDevice = () => {
    setSelectedDevice(null);
    setIsCreatingDevice(true);
    deviceForm.resetFields();
    deviceForm.setFieldsValue({
      is_active: true,
    });
    setIsDeviceModalVisible(true);
  };

  const handleSaveDevice = async () => {
    try {
      const values = await deviceForm.validateFields();

      if (isCreatingDevice) {
        await createDevice(values);
        message.success("设备创建成功");
      } else if (selectedDevice) {
        await updateDevice(selectedDevice.id, values);
        message.success("设备配置更新成功");
      }

      setIsDeviceModalVisible(false);
      loadDevices();
    } catch (error: any) {
      message.error(`保存失败: ${error.message}`);
    }
  };

  // ==================== 表格列定义 ====================

  const aiModelColumns = [
    { title: "模型名称", dataIndex: "model_name", key: "model_name" },
    { title: "提供商", dataIndex: "provider", key: "provider" },
    { title: "API Base", dataIndex: "api_base", key: "api_base", ellipsis: true },
    { 
      title: "默认", 
      dataIndex: "is_default", 
      key: "is_default",
      render: (val: boolean) => val ? "是" : "否"
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (val: boolean) => val ? "启用" : "禁用"
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: AIModel) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => handleEditAIModel(record)}>
          编辑
        </Button>
      ),
    },
  ];

  const agentColumns = [
    { title: "名称", dataIndex: "agent_name", key: "agent_name" },
    { title: "代码", dataIndex: "agent_code", key: "agent_code" },
    { title: "主机", dataIndex: "host", key: "host" },
    { title: "端口", dataIndex: "port", key: "port" },
    { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
    {
      title: "状态",
      dataIndex: "is_enabled",
      key: "is_enabled",
      render: (val: boolean) => val ? "启用" : "禁用"
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: Agent) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => handleEditAgent(record)}>
          编辑
        </Button>
      ),
    },
  ];

  const deviceColumns = [
    { title: "设备名称", dataIndex: "device_name", key: "device_name" },
    { title: "设备代码", dataIndex: "device_code", key: "device_code" },
    { title: "设备类型", dataIndex: "device_type", key: "device_type" },
    { title: "IP地址", dataIndex: "ip_address", key: "ip_address" },
    { title: "型号", dataIndex: "model", key: "model" },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (val: boolean) => val ? "启用" : "禁用"
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: Device) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => handleEditDevice(record)}>
          编辑
        </Button>
      ),
    },
  ];

  // ==================== 渲染 ====================

  const tabItems = [
    {
      key: "1",
      label: "AI 模型配置",
      children: (
        <Card>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateAIModel}>
              新增模型
            </Button>
          </Space>
          <Table
            dataSource={aiModels}
            columns={aiModelColumns}
            rowKey="id"
            loading={aiModelLoading}
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: "2",
      label: "Agent 配置",
      children: (
        <Card>
          <Table
            dataSource={agents}
            columns={agentColumns}
            rowKey="id"
            loading={agentLoading}
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: "3",
      label: "设备配置",
      children: (
        <Card>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateDevice}>
              新增设备
            </Button>
          </Space>
          <Table
            dataSource={devices}
            columns={deviceColumns}
            rowKey="id"
            loading={deviceLoading}
            pagination={false}
          />
        </Card>
      ),
    },
  ];

  return (
    <div className="setting-container">
      <Tabs activeKey={activeTab} items={tabItems} onChange={setActiveTab} />

      {/* AI模型编辑模态框 */}
      <Modal
        title={isCreatingAIModel ? "新增 AI 模型" : "编辑 AI 模型"}
        open={isAIModelModalVisible}
        onOk={handleSaveAIModel}
        onCancel={() => setIsAIModelModalVisible(false)}
        width={600}
      >
        <Form form={aiModelForm} layout="vertical">
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

      {/* Agent编辑模态框 */}
      <Modal
        title="编辑 Agent 配置"
        open={isAgentModalVisible}
        onOk={handleSaveAgent}
        onCancel={() => setIsAgentModalVisible(false)}
        width={500}
      >
        <Form form={agentForm} layout="vertical">
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

      {/* 设备编辑模态框 */}
      <Modal
        title={isCreatingDevice ? "新增设备" : "编辑设备配置"}
        open={isDeviceModalVisible}
        onOk={handleSaveDevice}
        onCancel={() => setIsDeviceModalVisible(false)}
        width={600}
      >
        <Form form={deviceForm} layout="vertical">
          <Form.Item label="设备代码" name="device_code" rules={[{ required: true }]}>
            <Input disabled={!isCreatingDevice} />
          </Form.Item>
          <Form.Item label="设备名称" name="device_name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="设备类型" name="device_type" rules={[{ required: true }]}>
            <Select disabled={!isCreatingDevice}>
              <Select.Option value="air_conditioner">空调</Select.Option>
              <Select.Option value="air_cleaner">空气净化器</Select.Option>
              <Select.Option value="lamp">灯具</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="关联Agent" name="agent_code" rules={[{ required: true }]}>
            <Select disabled={!isCreatingDevice}>
              {agents.map(agent => (
                <Select.Option key={agent.agent_code} value={agent.agent_code}>
                  {agent.agent_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="IP地址" name="ip_address">
            <Input />
          </Form.Item>
          <Form.Item label="Token" name="token">
            <Input.Password />
          </Form.Item>
          <Form.Item label="设备型号" name="model">
            <Input />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
        </Form.Item>
      </Form>
      </Modal>
    </div>
  );
};

export default Setting;
