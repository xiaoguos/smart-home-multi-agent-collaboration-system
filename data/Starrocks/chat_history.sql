-- ============================================
-- Moss AI 智能家居系统 - 对话记录表
-- 数据库: StarRocks
-- 用途: 存储用户与管家agent的对话记录
-- ============================================

CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;

-- ============================================
-- 对话记录表
-- ============================================
CREATE TABLE IF NOT EXISTS chat_history (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    created_at DATETIME COMMENT '创建时间',
    context_id VARCHAR(100) NOT NULL COMMENT '会话上下文ID',
    message_id VARCHAR(100) COMMENT '消息ID',
    task_id VARCHAR(100) COMMENT '任务ID',
    role VARCHAR(20) NOT NULL COMMENT '角色: user, agent, system',
    content STRING NOT NULL COMMENT '消息内容',
    status VARCHAR(20) COMMENT '状态: success, failed, error',
    error_message STRING COMMENT '错误信息（如果失败）',
    metadata STRING COMMENT '元数据（JSON格式）'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id, created_at)
DISTRIBUTED BY HASH(system_user_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- 创建索引（StarRocks通过DUPLICATE KEY和分桶键自动优化查询）
-- 查询优化: 按用户ID、会话ID、时间范围查询

-- ============================================
-- 对话列表表（会话列表）
-- ============================================
CREATE TABLE IF NOT EXISTS conversation_list (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    updated_at DATETIME COMMENT '最后更新时间',
    context_id VARCHAR(100) NOT NULL COMMENT '会话上下文ID（唯一标识）',
    title VARCHAR(200) COMMENT '对话标题',
    description VARCHAR(500) COMMENT '对话描述',
    message_count INT COMMENT '消息数量',
    last_message STRING COMMENT '最后一条消息内容（预览）',
    created_at DATETIME COMMENT '创建时间',
    is_active BOOLEAN COMMENT '是否激活'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id, updated_at)
DISTRIBUTED BY HASH(system_user_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 设备操作记录表
-- ============================================
CREATE TABLE IF NOT EXISTS device_operations (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    created_at DATETIME COMMENT '创建时间',
    context_id VARCHAR(100) COMMENT '会话上下文ID',
    device_type VARCHAR(50) NOT NULL COMMENT '设备类型: air_conditioner, air_cleaner, bedside_lamp',
    device_name VARCHAR(100) COMMENT '设备名称',
    action VARCHAR(100) NOT NULL COMMENT '操作动作',
    parameters STRING COMMENT '操作参数（JSON格式）',
    success BOOLEAN NOT NULL COMMENT '是否成功',
    response STRING COMMENT '操作响应',
    error_message STRING COMMENT '错误信息（如果失败）',
    execution_time INT COMMENT '执行时间（毫秒）'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id, created_at)
DISTRIBUTED BY HASH(system_user_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- 创建索引优化
-- 查询优化: 按用户ID、设备类型、时间范围、成功状态查询

