-- ============================================
-- Smart Home Multi-Agent Collaboration System 智能家居系统 - 对话记录表
-- 数据库: MySQL
-- 用途: 存储用户与管家agent的对话记录
-- ============================================

CREATE DATABASE IF NOT EXISTS moss_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE moss_ai;

-- ============================================
-- 对话记录表
-- ============================================
CREATE TABLE IF NOT EXISTS chat_history (
    id BIGINT AUTO_INCREMENT COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    context_id VARCHAR(100) NOT NULL COMMENT '会话上下文ID',
    message_id VARCHAR(100) COMMENT '消息ID',
    task_id VARCHAR(100) COMMENT '任务ID',
    role VARCHAR(20) NOT NULL COMMENT '角色: user, agent, system',
    content TEXT NOT NULL COMMENT '消息内容',
    status VARCHAR(20) DEFAULT 'success' COMMENT '状态: success, failed, error',
    error_message TEXT COMMENT '错误信息（如果失败）',
    metadata JSON COMMENT '元数据（JSON格式）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_user_context (system_user_id, context_id),
    KEY idx_created_at (created_at),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话记录表';

-- ============================================
-- 对话列表表（会话列表）
-- ============================================
CREATE TABLE IF NOT EXISTS conversation_list (
    id BIGINT AUTO_INCREMENT COMMENT '主键ID',
    context_id VARCHAR(100) NOT NULL COMMENT '会话上下文ID（唯一标识）',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    title VARCHAR(200) DEFAULT '新对话' COMMENT '对话标题',
    description VARCHAR(500) COMMENT '对话描述',
    message_count INT DEFAULT 0 COMMENT '消息数量',
    last_message TEXT COMMENT '最后一条消息内容（预览）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    PRIMARY KEY (id),
    UNIQUE KEY uk_context_id (context_id),
    KEY idx_user_updated (system_user_id, updated_at DESC),
    KEY idx_user_active (system_user_id, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话列表表';

-- ============================================
-- 设备操作记录表
-- ============================================
CREATE TABLE IF NOT EXISTS device_operations (
    id BIGINT AUTO_INCREMENT COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    context_id VARCHAR(100) COMMENT '会话上下文ID',
    device_type VARCHAR(50) NOT NULL COMMENT '设备类型: air_conditioner, air_cleaner, bedside_lamp',
    device_name VARCHAR(100) COMMENT '设备名称',
    action VARCHAR(100) NOT NULL COMMENT '操作动作',
    parameters JSON COMMENT '操作参数（JSON格式）',
    success BOOLEAN NOT NULL COMMENT '是否成功',
    response TEXT COMMENT '操作响应',
    error_message TEXT COMMENT '错误信息（如果失败）',
    execution_time INT COMMENT '执行时间（毫秒）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_user_device (system_user_id, device_type),
    KEY idx_created_at (created_at),
    KEY idx_success (success),
    KEY idx_context (context_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备操作记录表';

