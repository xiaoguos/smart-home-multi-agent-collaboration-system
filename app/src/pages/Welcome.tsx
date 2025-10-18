
import React from 'react';
import { Button, Typography, Space, Row, Col, Card } from 'antd';
import { 
    RobotOutlined, 
    MessageOutlined, 
    ThunderboltOutlined,
    BulbOutlined,
    SafetyOutlined,
    HomeOutlined,
    ControlOutlined,
    CheckCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './style/welcome.sass';

const { Title, Paragraph } = Typography;

const Welcome: React.FC = () => {
    const navigate = useNavigate();

    const handleStartChat = () => {
        navigate('/chat');
    };

    return (
        <div className="welcome-container">
            <div className="welcome-content">
                <Row gutter={[40, 40]} align="middle" justify="center">
                    {/* 左侧内容 */}
                    <Col xs={24} lg={8}>
                        <div className="left-content">
                            <Card className="feature-card">
                                <div className="card-header">
                                    <BulbOutlined className="card-icon" />
                                    <h3>智能特性</h3>
                                </div>
                                <div className="feature-list">
                                    <div className="feature-point">
                                        <CheckCircleOutlined className="check-icon" />
                                        <span>自然语言理解</span>
                                    </div>
                                    <div className="feature-point">
                                        <CheckCircleOutlined className="check-icon" />
                                        <span>多轮对话记忆</span>
                                    </div>
                                    <div className="feature-point">
                                        <CheckCircleOutlined className="check-icon" />
                                        <span>实时学习优化</span>
                                    </div>
                                    <div className="feature-point">
                                        <CheckCircleOutlined className="check-icon" />
                                        <span>个性化推荐</span>
                                    </div>
                                </div>
                            </Card>
                        </div>
                    </Col>

                    {/* 中间主要内容 */}
                    <Col xs={24} lg={8}>
                        <Space direction="vertical" size="large" align="center" className="welcome-space">
                            <div className="welcome-icon">
                                <RobotOutlined />
                            </div>
                            
                            <div className="welcome-text">
                                <Title level={1} className="welcome-title">
                                    欢迎使用 Moss AI
                                </Title>
                                <Paragraph className="welcome-description">
                                    您的智能AI助手，随时为您提供帮助和支持
                                </Paragraph>
                            </div>

                            <div className="welcome-features">
                                <Space size="large" wrap>
                                    <div className="feature-item">
                                        <MessageOutlined className="feature-icon" />
                                        <span>智能对话</span>
                                    </div>
                                    <div className="feature-item">
                                        <ThunderboltOutlined className="feature-icon" />
                                        <span>快速响应</span>
                                    </div>
                                    <div className="feature-item">
                                        <RobotOutlined className="feature-icon" />
                                        <span>AI驱动</span>
                                    </div>
                                </Space>
                            </div>

                            <Button 
                                type="primary" 
                                size="large" 
                                className="start-button"
                                onClick={handleStartChat}
                            >
                                开始使用
                            </Button>
                        </Space>
                    </Col>

                    {/* 右侧内容 */}
                    <Col xs={24} lg={8}>
                        <div className="right-content">
                            <Card className="advantages-card">
                                <div className="card-header">
                                    <SafetyOutlined className="card-icon" />
                                    <h3>核心优势</h3>
                                </div>
                                <div className="advantages-list">
                                    <div className="advantage-point">
                                        <HomeOutlined className="advantage-icon" />
                                        <div className="advantage-content">
                                            <div className="advantage-title">智能家居控制</div>
                                            <div className="advantage-desc">语音控制灯光、空调、窗帘等设备</div>
                                        </div>
                                    </div>
                                    <div className="advantage-point">
                                        <SafetyOutlined className="advantage-icon" />
                                        <div className="advantage-content">
                                            <div className="advantage-title">安全可靠</div>
                                            <div className="advantage-desc">企业级安全保障，数据隐私保护</div>
                                        </div>
                                    </div>
                                    <div className="advantage-point">
                                        <ControlOutlined className="advantage-icon" />
                                        <div className="advantage-content">
                                            <div className="advantage-title">场景联动</div>
                                            <div className="advantage-desc">智能场景设置，一键控制多个设备</div>
                                        </div>
                                    </div>
                                    <div className="advantage-point">
                                        <ThunderboltOutlined className="advantage-icon" />
                                        <div className="advantage-content">
                                            <div className="advantage-title">极速响应</div>
                                            <div className="advantage-desc">毫秒级响应，流畅对话体验</div>
                                        </div>
                                    </div>
                                </div>
                            </Card>
                        </div>
                    </Col>
                </Row>
            </div>
        </div>
    );
};

export default Welcome;