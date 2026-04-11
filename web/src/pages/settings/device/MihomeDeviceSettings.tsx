import {
  Button,
  Input,
  message,
  Table,
  Modal,
  Space,
  Tag,
  Badge,
  Descriptions,
} from "antd";
import React, { useState, useEffect } from "react";
import { ReloadOutlined } from "@ant-design/icons";
import "../styles/setting.sass";
import {
  getXiaomiDevices,
  type XiaomiDevice,
  type XiaomiDevicesResponse,
} from "../../../api/xiaomi";

const MihomeDeviceSettings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState<XiaomiDevice[]>([]);
  const [info, setInfo] = useState<XiaomiDevicesResponse["result"] | null>(null);
  const [selected, setSelected] = useState<XiaomiDevice | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const userStr = localStorage.getItem("user_info");
      if (!userStr) {
        message.error("请先登录系统账号");
        return;
      }
      const user = JSON.parse(userStr) as { id: number };
      const response = await getXiaomiDevices(user.id);
      if (response.code === 0) {
        setDevices(response.result.devices);
        setInfo(response.result);
        message.success(`已加载 ${response.result.total_devices} 台米家设备`);
      } else {
        message.error(response.message || "加载失败");
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      message.error(err.response?.data?.detail || err.message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const columns = [
    { title: "设备名称", dataIndex: "name", key: "name", width: 200 },
    { title: "家庭", dataIndex: "home_name", key: "home_name", width: 120 },
    { title: "型号", dataIndex: "model", key: "model", width: 180, ellipsis: true },
    { title: "IP地址", dataIndex: "localip", key: "localip", width: 130 },
    {
      title: "在线",
      dataIndex: "isOnline",
      key: "isOnline",
      width: 100,
      render: (val: boolean) => <Badge status={val ? "success" : "default"} text={val ? "在线" : "离线"} />,
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: unknown, record: XiaomiDevice) => (
        <Button
          type="link"
          onClick={() => {
            setSelected(record);
            setDetailOpen(true);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">米家设备</h2>
        <p className="setting-page-desc">从已绑定米家账号拉取在线设备列表，用于对照与排查</p>
      </div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button type="primary" icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
          刷新列表
        </Button>
        {info && (
          <Space>
            <Tag color="blue">服务器: {info.server}</Tag>
            <Tag color="green">家庭: {info.total_homes}</Tag>
            <Tag color="cyan">设备: {info.total_devices}</Tag>
          </Space>
        )}
      </Space>
      <Table
        dataSource={devices}
        columns={columns}
        rowKey="did"
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 台` }}
        scroll={{ x: 1000 }}
      />

      <Modal
        title="米家设备详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={[
          <Button key="c" onClick={() => setDetailOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {selected && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="设备名称" span={2}>
              {selected.name}
            </Descriptions.Item>
            <Descriptions.Item label="家庭">{selected.home_name}</Descriptions.Item>
            <Descriptions.Item label="在线">
              <Badge status={selected.isOnline ? "success" : "default"} text={selected.isOnline ? "在线" : "离线"} />
            </Descriptions.Item>
            <Descriptions.Item label="设备ID" span={2}>
              <Input.TextArea value={selected.did} autoSize={{ minRows: 1, maxRows: 2 }} readOnly />
            </Descriptions.Item>
            <Descriptions.Item label="型号" span={2}>
              {selected.model}
            </Descriptions.Item>
            <Descriptions.Item label="IP">{selected.localip || "-"}</Descriptions.Item>
            <Descriptions.Item label="MAC">{selected.mac || "-"}</Descriptions.Item>
            <Descriptions.Item label="Token" span={2}>
              <Input.TextArea value={selected.token} autoSize={{ minRows: 2, maxRows: 4 }} readOnly />
            </Descriptions.Item>
            {selected.parent_id && (
              <>
                <Descriptions.Item label="父设备ID" span={2}>
                  {selected.parent_id}
                </Descriptions.Item>
                <Descriptions.Item label="父设备型号" span={2}>
                  {selected.parent_model}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default MihomeDeviceSettings;
