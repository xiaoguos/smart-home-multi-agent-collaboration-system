import {
  Button,
  Cascader,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Mentions,
  Select,
  TreeSelect,
} from "antd";
import React from "react";
import "./style/setting.sass";

const Setting: React.FC = () => {
  const formItemLayout = {
    labelCol: {
      xs: { span: 24 },
      sm: { span: 6 },
    },
    wrapperCol: {
      xs: { span: 24 },
      sm: { span: 14 },
    },
  };
  const [form] = Form.useForm();
  const handleSubmit = () => {
    console.log(form.getFieldsValue());
  };
  return (
    <div>
      <Form
        {...formItemLayout}
        form={form}
        variant="filled"
        initialValues={{ username: "13716858579", password: "WDep@26056", region: "cn" }}
        style={{ maxWidth: 600 }}
      >
        <Form.Item
          label="米家账号手机号"
          name="username"
          rules={[{ required: true, message: "请输入手机号！" }]}
        >
          <Input placeholder="请输入手机号" style={{ width: "100%" }} />
        </Form.Item>

        <Form.Item
          label="米家账号密码"
          name="password"
          rules={[{ required: true, message: "请输入数字！" }]}
        >
          <Input.Password placeholder="请输入密码" style={{ width: "100%" }} />
        </Form.Item>

        <Form.Item
          label="设备所属区域"
          name="region"
          rules={[{ required: true, message: "请选择设备所属区域！" }]}
        >
          <Select
            placeholder="请选择设备所属区域"
            options={[
              { value: "cn", label: "中国" },
              { value: "en", label: "美国" },
              { value: "jp", label: "日本" },
            ]}
            style={{ width: "100%" }}
          />
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 6, span: 16 }}>
          <Button type="primary" onClick={handleSubmit}>
            保存
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default Setting;
