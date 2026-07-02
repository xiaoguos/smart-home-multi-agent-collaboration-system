

import React from "react";
import {
  Card,
  Row,
  Col,
  Typography,
  Divider,
  Tag,
  Space,
  Timeline,
  Descriptions,
  Button,
  Avatar,
  Badge,
} from "antd";
import {
  RobotOutlined,
  HomeOutlined,
  DatabaseOutlined,
  ApiOutlined,
  GithubOutlined,
  MailOutlined,
  PhoneOutlined,
  GlobalOutlined,
  CodeOutlined,
  CloudOutlined,
  SettingOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import "./about.sass";

const { Title, Paragraph, Text, Link } = Typography;

const About: React.FC = () => {
  const features = [
    {
      icon: <RobotOutlined />,
      title: "多Agent协作",
      description: "不同专业化的AI代理协同工作，提供专业化服务",
      color: "#1890ff",
    },
    {
      icon: <HomeOutlined />,
      title: "智能设备控制",
      description: "空调、空气净化器等设备的智能控制和管理",
      color: "#52c41a",
    },
    {
      icon: <DatabaseOutlined />,
      title: "数据分析与洞察",
      description: "深度挖掘用户行为数据，提供个性化建议",
      color: "#722ed1",
    },
    {
      icon: <ApiOutlined />,
      title: "统一管理接口",
      description: "通过总管理代理提供统一的智能家居控制接口",
      color: "#fa8c16",
    },
  ];

  const techStack = [
    { name: "LangChain", version: "0.1+", category: "AI框架" },
    { name: "DeepSeek", version: "最新", category: "大语言模型" },
    { name: "StarRocks", version: "3.0+", category: "数据库" },
    { name: "Redis", version: "7.0+", category: "缓存" },
    { name: "FastAPI", version: "0.100+", category: "Web框架" },
    { name: "Docker", version: "20.10+", category: "容器化" },
    { name: "Nginx", version: "1.20+", category: "反向代理" },
    { name: "React", version: "18.3+", category: "前端框架" },
    { name: "Tauri", version: "2.0+", category: "桌面应用" },
  ];

  const agents = [
    {
      name: "总管理代理",
      port: "12002",
      description: "统一协调所有子代理，提供一站式服务",
      status: "运行中",
      color: "#1890ff",
    },
    {
      name: "空调代理",
      port: "12000",
      description: "专业化的空调设备控制代理",
      status: "运行中",
      color: "#52c41a",
    },
    {
      name: "空气净化器代理",
      port: "12001",
      description: "空气净化器设备的智能控制",
      status: "运行中",
      color: "#722ed1",
    },
    {
      name: "数据挖掘代理",
      port: "12003",
      description: "用户行为分析和洞察生成",
      status: "运行中",
      color: "#fa8c16",
    },
  ];

  const roadmap = [
    {
      version: "v1.1.0",
      status: "计划中",
      features: ["支持更多智能设备类型", "增加语音控制功能", "实现设备联动场景"],
    },
    {
      version: "v1.2.0",
      status: "未来",
      features: ["支持多用户管理", "增加安全认证机制", "实现边缘计算支持"],
    },
    {
      version: "v2.0.0",
      status: "长期",
      features: ["支持联邦学习", "实现跨平台集成", "添加区块链溯源"],
    },
  ];

  return (
    <div className="about-page">
      <div className="about-hero">
        <div className="hero-content">
          <Avatar size={80} icon={<RobotOutlined />} className="hero-avatar" />
          <Title level={1} className="hero-title">
            Smart Home Multi-Agent Collaboration System
          </Title>
          <Title level={3} className="hero-subtitle">
            智能家居多Agent协作系统
          </Title>
          <Paragraph className="hero-description">
            基于LangChain和A2A架构的智能家居多Agent协作系统，通过多个专业化的AI代理协同工作，
            为用户提供智能化的家居控制体验。
          </Paragraph>
          <Space size="large">
            <Button 
              type="primary" 
              size="large" 
              icon={<GithubOutlined />}
              onClick={() => window.open('https://github.com/your-username/moss-ai', '_blank')}
            >
              GitHub
            </Button>
            <Button 
              size="large" 
              icon={<GlobalOutlined />}
              onClick={() => window.open('https://gitee.com/wdep/moss-ai', '_blank')}
            >
              Gitee
            </Button>
            <Button 
              size="large" 
              icon={<GlobalOutlined />}
              onClick={() => window.open('https://gitee.com/wdep/moss-ai', '_blank')}
            >
              在线演示
            </Button>
          </Space>
        </div>
      </div>

      <div className="about-content">
        {/* 核心特性 */}
        <section className="features-section">
          <Title level={2} className="section-title">
            <RobotOutlined /> 核心特性
          </Title>
          <Row gutter={[24, 24]}>
            {features.map((feature, index) => (
              <Col xs={24} sm={12} lg={6} key={index}>
                <Card
                  className="feature-card"
                  hoverable
                  style={{ borderColor: feature.color }}
                >
                  <div className="feature-icon" style={{ color: feature.color }}>
                    {feature.icon}
                  </div>
                  <Title level={4} className="feature-title">
                    {feature.title}
                  </Title>
                  <Paragraph className="feature-description">
                    {feature.description}
                  </Paragraph>
                </Card>
              </Col>
            ))}
          </Row>
        </section>

        <Divider />

        {/* 系统架构 */}
        <section className="architecture-section">
          <Title level={2} className="section-title">
            <SettingOutlined /> 系统架构
          </Title>
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="Agent服务" className="architecture-card">
                <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                  {agents.map((agent, index) => (
                    <div key={index} className="agent-item">
                      <div className="agent-header">
                        <Space>
                          <Badge
                            status="processing"
                            color={agent.color}
                            text={agent.name}
                          />
                          <Tag color={agent.color}>端口: {agent.port}</Tag>
                        </Space>
                      </div>
                      <Paragraph className="agent-description">
                        {agent.description}
                      </Paragraph>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="技术栈" className="architecture-card">
                <div className="tech-stack">
                  {techStack.map((tech, index) => (
                    <Tag
                      key={index}
                      className="tech-tag"
                      color="blue"
                      icon={<CodeOutlined />}
                    >
                      {tech.name} {tech.version}
                    </Tag>
                  ))}
                </div>
                <Divider />
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="AI框架">LangChain + LangGraph</Descriptions.Item>
                  <Descriptions.Item label="通信协议">A2A (Agent-to-Agent)</Descriptions.Item>
                  <Descriptions.Item label="数据库">StarRocks + Redis</Descriptions.Item>
                  <Descriptions.Item label="容器化">Docker + Docker Compose</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>
        </section>

        <Divider />

        {/* 开发路线图 */}
        <section className="roadmap-section">
          <Title level={2} className="section-title">
            <RobotOutlined /> 开发路线图
          </Title>
          <Timeline
            items={roadmap.map((item, index) => ({
              key: index,
              color: item.status === "计划中" ? "blue" : "green",
              label: item.version,
              children: (
                <Card size="small" className="roadmap-card">
                  <div className="roadmap-header">
                    <Title level={4} className="roadmap-version">
                      {item.version}
                    </Title>
                    <Tag color={item.status === "计划中" ? "blue" : "green"}>
                      {item.status}
                    </Tag>
                  </div>
                  <ul className="roadmap-features">
                    {item.features.map((feature, featureIndex) => (
                      <li key={featureIndex}>{feature}</li>
                    ))}
                  </ul>
                </Card>
              ),
            }))}
          />
        </section>

        <Divider />

        {/* 项目信息 */}
        <section className="project-info-section">
          <Title level={2} className="section-title">
            <TeamOutlined /> 项目信息
          </Title>
          <Row gutter={[24, 24]}>
            <Col xs={24} md={12}>
              <Card title="版本信息" className="info-card">
                <Descriptions column={1}>
                  <Descriptions.Item label="当前版本">v1.0.0</Descriptions.Item>
                  <Descriptions.Item label="发布日期">2024年12月</Descriptions.Item>
                  <Descriptions.Item label="许可证">MIT License</Descriptions.Item>
                  <Descriptions.Item label="开发语言">Python, TypeScript, Cangjie</Descriptions.Item>
                  <Descriptions.Item label="支持平台">Windows, macOS, Linux</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="联系方式" className="info-card">
                <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                  <div className="contact-item">
                    <GithubOutlined className="contact-icon" />
                    <Link href="https://github.com/your-username/moss-ai" target="_blank">
                      GitHub 仓库
                    </Link>
                  </div>
                  <div className="contact-item">
                    <GlobalOutlined className="contact-icon" />
                    <Link href="https://gitee.com/wdep/moss-ai" target="_blank">
                      Gitee 仓库
                    </Link>
                  </div>
                  <div className="contact-item">
                    <MailOutlined className="contact-icon" />
                    <Link href="mailto:chenzhengchen2004@gmail.com">
                      chenzhengchen2004@gmail.com
                    </Link>
                  </div>
                  <div className="contact-item">
                    <GlobalOutlined className="contact-icon" />
                    <Link href="https://gitee.com/wdep/moss-ai" target="_blank">
                      项目主页
                    </Link>
                  </div>
                  <div className="contact-item">
                    <PhoneOutlined className="contact-icon" />
                    <Text>技术交流群: 扫描二维码加入</Text>
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>
        </section>

        <Divider />

        {/* 致谢 */}
        <section className="acknowledgments-section">
          <Title level={2} className="section-title">
            <CloudOutlined /> 致谢
          </Title>
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8} md={6}>
              <Card size="small" className="acknowledgment-card">
                <div className="acknowledgment-content">
                  <Title level={5}>LangChain</Title>
                  <Text type="secondary">强大的LLM应用开发框架</Text>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small" className="acknowledgment-card">
                <div className="acknowledgment-content">
                  <Title level={5}>A2A SDK</Title>
                  <Text type="secondary">Agent间通信协议</Text>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small" className="acknowledgment-card">
                <div className="acknowledgment-content">
                  <Title level={5}>StarRocks</Title>
                  <Text type="secondary">高性能分析型数据库</Text>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small" className="acknowledgment-card">
                <div className="acknowledgment-content">
                  <Title level={5}>DeepSeek</Title>
                  <Text type="secondary">优秀的大语言模型服务</Text>
                </div>
              </Card>
            </Col>
          </Row>
        </section>
      </div>
    </div>
  );
};

export default About;