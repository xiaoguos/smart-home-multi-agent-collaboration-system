-- ============================================
-- Moss AI 智能家居系统 - AI模型配置脚本
-- 数据库: StarRocks
-- 用途: 创建 AI 模型配置表并插入默认配置
-- ============================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;

-- ============================================
-- 创建 AI 模型配置表
-- ============================================
CREATE TABLE IF NOT EXISTS ai_model_config (
    id BIGINT NOT NULL COMMENT '配置ID',
    system_user_id BIGINT COMMENT '系统用户ID，NULL表示全局配置',
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

-- 清空现有的 AI 模型配置（可选，重新初始化时使用）
-- DELETE FROM ai_model_config;

-- ============================================
-- 插入 AI 模型配置数据
-- ============================================

-- DeepSeek 模型（全局默认配置）
INSERT INTO ai_model_config (
    id,
    system_user_id,
    model_name, 
    provider, 
    api_key, 
    api_base, 
    model_type, 
    temperature, 
    max_tokens, 
    is_default, 
    is_active,
    created_at,
    updated_at
) VALUES (
    1,
    NULL,  -- NULL表示全局配置，适用于所有用户
    'deepseek-chat',
    'deepseek',
    'sk-0f603ccc4af94854ac560c59f223b1d5',
    'https://api.deepseek.com',
    'chat',
    0.0,
    2048,
    TRUE,
    TRUE,
    NOW(),
    NOW()
);

-- OpenAI 模型（备用，默认禁用）
-- 如需使用，请修改 api_key 并将 is_active 设为 TRUE
INSERT INTO ai_model_config (
    id,
    system_user_id,
    model_name, 
    provider, 
    api_key, 
    api_base, 
    model_type, 
    temperature, 
    max_tokens, 
    is_default, 
    is_active,
    created_at,
    updated_at
) VALUES (
    2,
    NULL,  -- NULL表示全局配置
    'gpt-3.5-turbo',
    'openai',
    'your-openai-api-key',
    'https://api.openai.com/v1',
    'chat',
    0.7,
    2048,
    FALSE,
    FALSE,
    NOW(),
    NOW()
);

-- GPT-4 模型（备用，默认禁用）
-- 如需使用，请修改 api_key 并将 is_active 设为 TRUE
INSERT INTO ai_model_config (
    id,
    system_user_id,
    model_name, 
    provider, 
    api_key, 
    api_base, 
    model_type, 
    temperature, 
    max_tokens, 
    is_default, 
    is_active,
    created_at,
    updated_at
) VALUES (
    3,
    NULL,  -- NULL表示全局配置
    'gpt-4',
    'openai',
    'your-openai-api-key',
    'https://api.openai.com/v1',
    'chat',
    0.7,
    4096,
    FALSE,
    FALSE,
    NOW(),
    NOW()
);

-- ============================================
-- 使用说明
-- ============================================
-- 1. system_user_id 为 NULL 的配置为全局配置，适用于所有用户
-- 2. system_user_id 有值的配置为用户专属配置，优先级高于全局配置
-- 3. 查询时优先使用用户专属配置，如无则使用全局配置
-- 
-- 示例：为 admin 用户（ID=1000000001）添加专属配置
-- INSERT INTO ai_model_config (
--     id, system_user_id, model_name, provider, api_key, api_base,
--     model_type, temperature, max_tokens, is_default, is_active,
--     created_at, updated_at
-- ) VALUES (
--     4, 1000000001, 'deepseek-chat', 'deepseek', 'user-specific-key',
--     'https://api.deepseek.com', 'chat', 0.0, 2048, TRUE, TRUE, NOW(), NOW()
-- );
