import {
  Button,
  Form,
  Input,
  Select,
  Switch,
  message,
  Table,
  Modal,
  Space,
} from "antd";
import React, { useState, useEffect } from "react";
import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import "../styles/setting.sass";
import {
  getAgents,
  getDevices,
  updateDevice,
  createDevice,
  type Agent,
  type Device,
} from "../../../api/config";

const LocalDeviceSettings: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selected, setSelected] = useState<Device | null>(null);
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const loadAgents = async () => {
    try {
      setAgents(await getAgents());
    } catch {
      /* ignore */
    }
  };

  const loadDevices = async () => {
    try {
      setLoading(true);
      setDevices(await getDevices());
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`加载设备失败: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAgents();
    void loadDevices();
  }, []);

  const openEdit = (d: Device) => {
    setSelected(d);
    setCreating(false);
    form.setFieldsValue(d);
    setModalOpen(true);
  };

  const openCreate = () => {
    setSelected(null);
    setCreating(true);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      if (creating) {
        await createDevice(values);
        message.success("设备已创建");
      } else if (selected) {
        await updateDevice(selected.id, values);
        message.success("设备已更新");
      }
      setModalOpen(false);
      void loadDevices();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      message.error(`保存失败: ${msg}`);
    }
  };

  const columns = [
    { title: "设备名称", dataIndex: "device_name", key: "device_name" },
    { title: "设备代码", dataIndex: "device_code", key: "device_code" },
    { title: "设备类型", dataIndex: "device_type", key: "device_type" },
    { title: "IP地址", dataIndex: "ip_address", key: "ip_address" },
    { title: "型号", dataIndex: "model", key: "model" },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (val: boolean) => (val ? "启用" : "禁用"),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: Device) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          编辑
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">本地设备</h2>
        <p className="setting-page-desc">维护与 Agent 关联的本地设备清单（数据库中的 device_config）</p>
      </div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增设备
        </Button>
      </Space>
      <Table dataSource={devices} columns={columns} rowKey="id" loading={loading} pagination={false} />

      <Modal title={creating ? "新增设备" : "编辑设备"} open={modalOpen} onOk={() => void save()} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item label="设备代码" name="device_code" rules={[{ required: true }]}>
            <Input disabled={!creating} />
          </Form.Item>
          <Form.Item label="设备名称" name="device_name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="设备类型" name="device_type" rules={[{ required: true }]}>
            <Select disabled={!creating}>
              <Select.Option value="air_conditioner">空调</Select.Option>
              <Select.Option value="air_cleaner">空气净化器</Select.Option>
              <Select.Option value="lamp">灯具</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="关联Agent" name="agent_code" rules={[{ required: true }]}>
            <Select disabled={!creating}>
              {agents.map((a) => (
                <Select.Option key={a.agent_code} value={a.agent_code}>
                  {a.agent_name}
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
    </>
  );
};

export default LocalDeviceSettings;
