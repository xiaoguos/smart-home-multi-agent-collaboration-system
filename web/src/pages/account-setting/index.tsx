import React, { useState, useEffect } from 'react';
import { Card, Button, message, Space, Typography, Tag, Spin, Modal } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, LinkOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getUserInfo } from '../../api/auth';
import { checkXiaomiBindingStatus, unbindXiaomiAccount, type BindingStatus } from '../../api/xiaomi';
import { checkDidaBindingStatus, unbindDidaAccount, type DidaBindingStatusResponse } from '../../api/dida';
import Header from '../../components/Header';
import './account-setting.sass';

const { Title, Text } = Typography;

const AccountSetting: React.FC = () => {
  const navigate = useNavigate();
  const [xiaomiLoading, setXiaomiLoading] = useState(false);
  const [didaLoading, setDidaLoading] = useState(false);
  const [bindingStatus, setBindingStatus] = useState<BindingStatus | null>(null);
  const [didaBindingStatus, setDidaBindingStatus] = useState<DidaBindingStatusResponse | null>(null);
  const userInfo = getUserInfo();

  useEffect(() => {
    loadBindingStatus();
    loadDidaBindingStatus();
  }, []);

  const loadBindingStatus = async () => {
    if (!userInfo) return;

    try {
      setXiaomiLoading(true);
      const status = await checkXiaomiBindingStatus(userInfo.id);
      setBindingStatus(status);
    } catch (error: any) {
      console.error('加载小米账号绑定状态失败:', error);
      message.error('加载小米绑定状态失败');
    } finally {
      setXiaomiLoading(false);
    }
  };

  const loadDidaBindingStatus = async () => {
    if (!userInfo) return;

    try {
      setDidaLoading(true);
      const status = await checkDidaBindingStatus(userInfo.id);
      setDidaBindingStatus(status);
    } catch (error: any) {
      console.error('加载滴答清单绑定状态失败:', error);
      message.error('加载滴答清单绑定状态失败');
    } finally {
      setDidaLoading(false);
    }
  };

  const handleBindXiaomi = () => {
    navigate('/xiaomi-binding');
  };

  const handleUnbindXiaomi = () => {
    if (!userInfo) return;

    Modal.confirm({
      title: '确认解绑小米账号',
      icon: <ExclamationCircleOutlined />,
      content: '解绑后，将无法通过 Moss AI 助手控制小米智能家居设备。您确定要解绑吗？',
      okText: '确认解绑',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await unbindXiaomiAccount(userInfo.id);
          message.success('小米账号已解绑');
          // 重新加载绑定状态
          loadBindingStatus();
        } catch (error: any) {
          console.error('解绑小米账号失败:', error);
          message.error(error.response?.data?.detail || '解绑失败，请稍后重试');
        }
      },
    });
  };

  const handleBindDida = () => {
    navigate('/dida-binding');
  };

  const handleUnbindDida = () => {
    if (!userInfo) return;

    Modal.confirm({
      title: '确认解绑滴答清单账号',
      icon: <ExclamationCircleOutlined />,
      content: '解绑后，将无法通过 Moss AI 助手管理您的滴答清单任务。您确定要解绑吗？',
      okText: '确认解绑',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await unbindDidaAccount(userInfo.id);
          message.success('滴答清单账号已解绑');
          // 重新加载绑定状态
          loadDidaBindingStatus();
        } catch (error: any) {
          console.error('解绑滴答清单账号失败:', error);
          message.error(error.response?.data?.detail || '解绑失败，请稍后重试');
        }
      },
    });
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
            <Spin spinning={xiaomiLoading}>
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
                      <Space>
                        <Button 
                          type="default" 
                          onClick={handleBindXiaomi}
                        >
                          重新绑定
                        </Button>
                        <Button 
                          danger
                          onClick={handleUnbindXiaomi}
                        >
                          解绑账号
                        </Button>
                      </Space>
                      <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
                        解绑后需重新授权才能使用相关功能
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

          {/* 滴答清单账号绑定状态 */}
          <Card
            title="滴答清单账号绑定"
            className="binding-card"
            extra={
              !didaBindingStatus?.is_bound && (
                <Button 
                  type="primary" 
                  icon={<LinkOutlined />}
                  onClick={handleBindDida}
                >
                  绑定滴答清单
                </Button>
              )
            }
          >
            <Spin spinning={didaLoading}>
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div className="status-row">
                  <Text strong>绑定状态：</Text>
                  {didaBindingStatus?.is_bound ? (
                    <Tag icon={<CheckCircleOutlined />} color="success">
                      已绑定
                    </Tag>
                  ) : (
                    <Tag icon={<CloseCircleOutlined />} color="default">
                      未绑定
                    </Tag>
                  )}
                </div>

                {didaBindingStatus?.is_bound && (
                  <>
                    <div className="status-row">
                      <Text strong>滴答清单账号：</Text>
                      <Text>{didaBindingStatus.username}</Text>
                    </div>

                    {didaBindingStatus.bound_at && (
                      <div className="status-row">
                        <Text strong>绑定时间：</Text>
                        <Text type="secondary">
                          {new Date(didaBindingStatus.bound_at).toLocaleString('zh-CN')}
                        </Text>
                      </div>
                    )}

                    {didaBindingStatus.token_expires_at && (
                      <div className="status-row">
                        <Text strong>令牌过期时间：</Text>
                        <Text type="secondary">
                          {new Date(didaBindingStatus.token_expires_at).toLocaleString('zh-CN')}
                        </Text>
                      </div>
                    )}

                    <div className="rebind-section">
                      <Space>
                        <Button 
                          type="default" 
                          onClick={handleBindDida}
                        >
                          重新绑定
                        </Button>
                        <Button 
                          danger
                          onClick={handleUnbindDida}
                        >
                          解绑账号
                        </Button>
                      </Space>
                      <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
                        解绑后需重新授权才能使用相关功能
                      </Text>
                    </div>
                  </>
                )}

                {!didaBindingStatus?.is_bound && (
                  <div className="binding-hint">
                    <Text type="secondary">
                      绑定滴答清单账号后，您可以通过 Moss AI 助手管理您的待办事项、创建任务等
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

