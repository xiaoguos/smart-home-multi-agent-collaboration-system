-- ============================================
-- Smart Home Multi-Agent Collaboration System 智能家居系统 - AI模型配置脚本
-- 数据库: MySQL
-- 用途: 创建 AI 模型配置表并插入默认配置
-- ============================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS moss_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE moss_ai;

-- ============================================
-- 创建 AI 模型配置表
-- ============================================
CREATE TABLE IF NOT EXISTS ai_model_config (
    id BIGINT AUTO_INCREMENT COMMENT '配置ID',
    model_name VARCHAR(100) NOT NULL COMMENT '模型名称',
    provider VARCHAR(50) NOT NULL COMMENT '提供商: deepseek, openai, baidu',
    api_key VARCHAR(500) NOT NULL COMMENT 'API密钥',
    api_base VARCHAR(200) NOT NULL COMMENT 'API基础URL',
    model_type VARCHAR(50) DEFAULT 'chat' COMMENT '模型类型: chat, embedding, search',
    temperature DOUBLE DEFAULT 0.7 COMMENT '温度参数',
    max_tokens INT DEFAULT 2048 COMMENT '最大token数',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否为默认模型',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_model_name (model_name),
    KEY idx_provider (provider),
    KEY idx_default_active (is_default, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI模型配置表';

-- 清空现有的 AI 模型配置（可选，重新初始化时使用）
-- DELETE FROM ai_model_config;

-- ============================================
-- 插入 AI 模型配置数据
-- ============================================

-- DeepSeek 模型（默认）
INSERT INTO ai_model_config (
    model_name, 
    provider, 
    api_key, 
    api_base, 
    temperature, 
    is_default
) VALUES (
    'deepseek-chat',
    'deepseek',
    'sk-0f603ccc4af94854ac560c59f223b1d5',
    'https://api.deepseek.com',
    0.0,
    TRUE
);

-- OpenAI 模型（备用，默认禁用）
-- 如需使用，请修改 api_key 并将 is_active 设为 TRUE
INSERT INTO ai_model_config (
    model_name, 
    provider, 
    api_key, 
    api_base,
    is_active
) VALUES (
    'gpt-3.5-turbo',
    'openai',
    'your-openai-api-key',
    'https://api.openai.com/v1',
    FALSE
);

-- GPT-4 模型（备用，默认禁用）
-- 如需使用，请修改 api_key 并将 is_active 设为 TRUE
INSERT INTO ai_model_config (
    model_name, 
    provider, 
    api_key, 
    api_base,
    max_tokens,
    is_active
) VALUES (
    'gpt-4',
    'openai',
    'your-openai-api-key',
    'https://api.openai.com/v1',
    4096,
    FALSE
);

-- ============================================
-- 索引已在建表时创建
-- ============================================

-- ============================================
-- AI 模型配置说明
-- ============================================
-- 
-- model_name: 模型名称，用于调用时识别
-- provider: 提供商（deepseek, openai, baidu 等）
-- api_key: API 密钥，请替换为实际的密钥
-- api_base: API 基础 URL
-- model_type: 模型类型（chat, embedding, search）
-- temperature: 温度参数（0-2），控制输出随机性
--   - 0: 确定性输出，适合精确任务
--   - 0.7: 平衡创造性和准确性
--   - 1.0+: 更有创造性的输出
-- max_tokens: 最大 token 数量
-- is_default: 是否为默认模型（系统启动时使用）
-- is_active: 是否启用该模型
-- 
-- ============================================
-- 使用说明
-- ============================================
-- 
-- 1. 首次使用：
--    执行此脚本插入默认 AI 模型配置
--    mysql -h localhost -P 3306 -u root -p < data/Mysql/ai_config.sql
-- 
-- 2. 修改 API Key：
--    UPDATE ai_model_config 
--    SET api_key = '你的新密钥' 
--    WHERE model_name = 'deepseek-chat';
-- 
-- 3. 切换默认模型：
--    -- 先将所有模型设为非默认
--    UPDATE ai_model_config SET is_default = FALSE;
--    -- 再设置新的默认模型
--    UPDATE ai_model_config 
--    SET is_default = TRUE 
--    WHERE model_name = 'gpt-4';
-- 
-- 4. 添加新模型：
--    INSERT INTO ai_model_config (...) VALUES (...);
-- 
-- ============================================

