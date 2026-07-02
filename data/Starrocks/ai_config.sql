-- ============================================
-- Smart Home Multi-Agent Collaboration System 智能家居系统 - AI模型配置脚本
-- 数据库: StarRocks
-- 用途: 创建 AI 模型配置表并插入默认配置
-- ============================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS moss_ai;
USE moss_ai;

-- ============================================
-- 创建 AI 模型配置表
-- ============================================
CREATE TABLE IF NOT EXISTS ai_model_config (
    id BIGINT NOT NULL COMMENT '配置ID',
    model_name VARCHAR(100) NOT NULL COMMENT '模型名称',
    provider VARCHAR(50) NOT NULL COMMENT '提供商: deepseek, openai, baidu',
    api_key VARCHAR(500) NOT NULL COMMENT 'API密钥',
    api_base VARCHAR(200) NOT NULL COMMENT 'API基础URL',
    model_type VARCHAR(50) COMMENT '模型类型: chat, embedding, search',
    temperature DOUBLE COMMENT '温度参数',
    max_tokens INT COMMENT '最大token数',
    is_default BOOLEAN COMMENT '是否为默认模型',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
PRIMARY KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);
