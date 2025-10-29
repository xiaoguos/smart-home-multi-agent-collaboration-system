import React, { useState, useEffect } from 'react';
import { Card, Button, message, Space, Typography, Tag, Spin } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, LinkOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getUserInfo } from '../api/auth';
import { checkXiaomiBindingStatus, type BindingStatus } from '../api/xiaomi';
import Header from '../components/Header';
import './style/account-setting.sass';

const { Title, Text } = Typography;

const AccountSetting: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [bindingStatus, setBindingStatus] = useState<BindingStatus | null>(null);
  const userInfo = getUserInfo();

  useEffect(() => {
    loadBindingStatus();
  }, []);

  const loadBindingStatus = async () => {
    if (!userInfo) return;

    try {
      setLoading(true);
      const status = await checkXiaomiBindingStatus(userInfo.id);
      setBindingStatus(status);
    } catch (error: any) {
      console.error('加载小米账号绑定状态失败:', error);
      message.error('加载绑定状态失败');
    } finally {
      setLoading(false);
    }
  };

  const handleBindXiaomi = () => {
    navigate('/xiaomi-binding');
  };

  return (
    <div className="account-setting-page">
      <Header />
      <div className="account-setting-container">
        <div className="setting-content">
          <Title level={2}>账户设置</Title>
          
          {/* 小米账号绑定状态 */}
          <Card
            title="小米账号绑定"
            className="binding-card"
            extra={
              !bindingStatus?.is_bound && (
                <Button 
                  type="primary" 
                  icon={<LinkOutlined />}
                  onClick={handleBindXiaomi}
                >
                  绑定小米账号
                </Button>
              )
            }
          >
            <Spin spinning={loading}>
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div className="status-row">
                  <Text strong>绑定状态：</Text>
                  {bindingStatus?.is_bound ? (
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
                        <Text type="secondary">
                          {new Date(bindingStatus.bound_at).toLocaleString('zh-CN')}
                        </Text>
                      </div>
                    )}

                    <div className="rebind-section">
                      <Button 
                        type="default" 
                        onClick={handleBindXiaomi}
                      >
                        重新绑定
                      </Button>
                      <Text type="secondary" style={{ marginLeft: 12 }}>
                        重新绑定将覆盖当前绑定的小米账号
                      </Text>
                    </div>
                  </>
                )}

                {!bindingStatus?.is_bound && (
                  <div className="binding-hint">
                    <Text type="secondary">
                      绑定小米账号后，您可以通过 Moss AI 控制小米智能家居设备
                    </Text>
                  </div>
                )}
              </Space>
            </Spin>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AccountSetting;

