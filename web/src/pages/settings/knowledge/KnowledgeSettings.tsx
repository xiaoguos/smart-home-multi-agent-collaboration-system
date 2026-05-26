import React, { useState, useEffect } from 'react';
import {
  Button, Card, Col, Collapse, Form, Input, message, Modal,
  Popconfirm, Row, Select, Space, Statistic, Table, Tag, Typography, Upload,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload/interface';
import {
  BookOutlined, CloudUploadOutlined, DeleteOutlined,
  PlusOutlined, SearchOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import {
  addDocument, deleteDocument, getKBStats, listDocuments,
  queryKnowledgeBase, uploadKBFile,
  type KBChunk, type KBDocument, type KBStats,
} from '../../../api/knowledgeBase';
import '../styles/setting.sass';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

const CATEGORIES = ['通用', '智能家居', '家电说明', '操作手册', '故障排查', '保养建议', '其他'];

const KnowledgeSettings: React.FC = () => {
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [stats, setStats] = useState<KBStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [_statsLoading, setStatsLoading] = useState(false);

  // 添加文档 modal
  const [addOpen, setAddOpen] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [addForm] = Form.useForm();

  // 上传文件
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploadCategory, setUploadCategory] = useState('通用');

  // 测试查询
  const [queryText, setQueryText] = useState('');
  const [queryCategory, setQueryCategory] = useState<string | undefined>(undefined);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResults, setQueryResults] = useState<KBChunk[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await listDocuments();
      setDocs(res.documents);
    } catch (e: unknown) {
      message.error(`加载失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      setStats(await getKBStats());
    } catch {
      // stats 不影响主流程
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    void load();
    void loadStats();
  }, []);

  // ── 添加文档 ──────────────────────────────────────────
  const handleAdd = async () => {
    const values = await addForm.validateFields();
    setAddLoading(true);
    try {
      await addDocument(values);
      message.success('文档已写入知识库');
      addForm.resetFields();
      setAddOpen(false);
      await load();
      await loadStats();
    } catch (e: unknown) {
      message.error(`写入失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setAddLoading(false);
    }
  };

  // ── 上传文件 ──────────────────────────────────────────
  const handleUpload = async () => {
    if (!fileList.length || !fileList[0].originFileObj) {
      message.warning('请先选择文件');
      return;
    }
    setUploadLoading(true);
    try {
      await uploadKBFile(fileList[0].originFileObj as File, uploadCategory);
      message.success('文件已写入知识库');
      setFileList([]);
      setUploadOpen(false);
      await load();
      await loadStats();
    } catch (e: unknown) {
      message.error(`上传失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setUploadLoading(false);
    }
  };

  // ── 删除文档 ──────────────────────────────────────────
  const handleDelete = async (docId: string) => {
    try {
      await deleteDocument(docId);
      message.success('文档已删除');
      await load();
      await loadStats();
    } catch (e: unknown) {
      message.error(`删除失败: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  // ── 测试查询 ──────────────────────────────────────────
  const handleQuery = async () => {
    if (!queryText.trim()) { message.warning('请输入查询内容'); return; }
    setQueryLoading(true);
    try {
      const res = await queryKnowledgeBase({ query: queryText, top_k: 5, category: queryCategory });
      setQueryResults(res.results);
    } catch (e: unknown) {
      message.error(`查询失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setQueryLoading(false);
    }
  };

  // ── 表格列 ───────────────────────────────────────────
  const columns: ColumnsType<KBDocument> = [
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (t) => <Text strong>{t}</Text>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 110,
      render: (c) => <Tag color="blue">{c}</Tag>,
    },
    {
      title: '片段数',
      dataIndex: 'total_chunks',
      width: 80,
      align: 'center',
      render: (n) => <Tag color="green">{n}</Tag>,
    },
    {
      title: '内容预览',
      dataIndex: 'preview',
      ellipsis: true,
      render: (p) => <Text type="secondary" style={{ fontSize: 12 }}>{p}</Text>,
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 120,
      ellipsis: true,
      render: (s) => s ? <Text type="secondary" style={{ fontSize: 12 }}>{s}</Text> : '-',
    },
    {
      title: '操作',
      width: 80,
      align: 'center',
      render: (_, row) => (
        <Popconfirm
          title="确认删除该文档？"
          description="删除后无法恢复，知识库将不再包含该文档内容。"
          onConfirm={() => handleDelete(row.doc_id)}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      {/* 标题 & 操作 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Space align="center">
          <BookOutlined style={{ fontSize: 22, color: '#1677ff' }} />
          <Title level={4} style={{ margin: 0 }}>知识库管理</Title>
        </Space>
        <Space>
          <Button icon={<CloudUploadOutlined />} onClick={() => setUploadOpen(true)}>上传文件</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>添加文档</Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 20 }}>
          <Col span={6}>
            <Card size="small" style={{ borderRadius: 8 }}>
              <Statistic
                title="文档总数"
                value={stats.total_documents}
                prefix={<DatabaseOutlined />}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ borderRadius: 8 }}>
              <Statistic
                title="向量片段数"
                value={stats.total_chunks}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" style={{ borderRadius: 8, height: '100%' }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>分类分布</div>
              <Space wrap>
                {Object.entries(stats.categories).map(([cat, count]) => (
                  <Tag key={cat} color="blue">{cat} ({count})</Tag>
                ))}
                {!Object.keys(stats.categories).length && <Text type="secondary">暂无数据</Text>}
              </Space>
            </Card>
          </Col>
        </Row>
      )}

      {/* 文档列表 */}
      <Card
        title={<Space><BookOutlined />文档列表</Space>}
        style={{ marginBottom: 20, borderRadius: 8 }}
        extra={<Button size="small" onClick={() => { void load(); void loadStats(); }}>刷新</Button>}
      >
        <Table
          rowKey="doc_id"
          dataSource={docs}
          columns={columns}
          loading={loading}
          size="small"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{ emptyText: '知识库为空，点击「添加文档」或「上传文件」开始构建' }}
        />
      </Card>

      {/* 测试查询面板 */}
      <Collapse ghost style={{ marginBottom: 20 }}>
        <Panel header={<Space><SearchOutlined />测试查询（验证知识库检索效果）</Space>} key="query">
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <Select
              placeholder="按分类过滤（可选）"
              allowClear
              style={{ width: 160 }}
              options={CATEGORIES.map((c) => ({ label: c, value: c }))}
              onChange={setQueryCategory}
            />
            <Input
              placeholder="输入查询内容，如：空调如何保养"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onPressEnter={handleQuery}
              style={{ flex: 1 }}
            />
            <Button type="primary" icon={<SearchOutlined />} loading={queryLoading} onClick={handleQuery}>
              查询
            </Button>
          </Space.Compact>

          {queryResults.length > 0 && (
            <div>
              {queryResults.map((r, _i) => (
                <Card
                  key={`${r.doc_id}_${r.chunk_index}`}
                  size="small"
                  style={{ marginBottom: 8, borderRadius: 6 }}
                  title={
                    <Space>
                      <Tag color="blue">{r.category}</Tag>
                      <Text strong style={{ fontSize: 13 }}>{r.title}</Text>
                      <Tag color={r.score > 0.8 ? 'green' : r.score > 0.6 ? 'orange' : 'default'}>
                        相关度 {(r.score * 100).toFixed(0)}%
                      </Tag>
                    </Space>
                  }
                >
                  <Paragraph style={{ margin: 0, fontSize: 13, whiteSpace: 'pre-wrap' }}>
                    {r.text}
                  </Paragraph>
                </Card>
              ))}
            </div>
          )}
          {queryResults.length === 0 && !queryLoading && queryText && (
            <Text type="secondary">未找到相关内容</Text>
          )}
        </Panel>
      </Collapse>

      {/* 添加文档 Modal */}
      <Modal
        title={<Space><PlusOutlined />添加文档到知识库</Space>}
        open={addOpen}
        onOk={handleAdd}
        onCancel={() => { setAddOpen(false); addForm.resetFields(); }}
        confirmLoading={addLoading}
        okText="写入知识库"
        width={640}
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" initialValues={{ category: '通用' }}>
          <Form.Item name="title" label="文档标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="如：海尔空调 KFR-35 使用说明" />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Select options={CATEGORIES.map((c) => ({ label: c, value: c }))} />
          </Form.Item>
          <Form.Item name="source" label="来源（可选）">
            <Input placeholder="如：官方说明书 P12-15" />
          </Form.Item>
          <Form.Item
            name="content"
            label="文档内容"
            rules={[{ required: true, message: '请输入文档内容' }]}
          >
            <TextArea
              rows={10}
              placeholder="粘贴文档内容，系统会自动切分为向量片段存储..."
              showCount
              maxLength={20000}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 上传文件 Modal */}
      <Modal
        title={<Space><CloudUploadOutlined />上传文件到知识库</Space>}
        open={uploadOpen}
        onOk={handleUpload}
        onCancel={() => { setUploadOpen(false); setFileList([]); }}
        confirmLoading={uploadLoading}
        okText="上传并写入"
        destroyOnClose
      >
        <Form layout="vertical">
          <Form.Item label="文件分类">
            <Select
              value={uploadCategory}
              onChange={setUploadCategory}
              options={CATEGORIES.map((c) => ({ label: c, value: c }))}
            />
          </Form.Item>
          <Form.Item label="选择文件（支持 .txt / .md）">
            <Upload
              accept=".txt,.md"
              maxCount={1}
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: fl }) => setFileList(fl)}
            >
              <Button icon={<CloudUploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
        </Form>
        <Text type="secondary" style={{ fontSize: 12 }}>
          文件会被自动切分为多个向量片段，支持中文内容。
        </Text>
      </Modal>
    </div>
  );
};

export default KnowledgeSettings;
