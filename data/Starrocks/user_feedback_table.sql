-- ============================================
-- 用户反馈表 - 用于存储用户对推荐操作的修改
-- ============================================

USE moss_ai;

-- ============================================
-- 用户反馈记录表
-- ============================================
CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    created_at DATETIME COMMENT '创建时间',
    context_id VARCHAR(100) COMMENT '会话上下文ID',
    original_recommendation STRING COMMENT '原始推荐（JSON格式）',
    user_modification STRING COMMENT '用户修改后的操作（JSON格式）',
    scene_matched VARCHAR(100) COMMENT '匹配的场景',
    time_period VARCHAR(20) COMMENT '时间段（早上/下午/晚上/夜晚）',
    feedback_type VARCHAR(20) COMMENT '反馈类型：accepted, modified, rejected',
    confidence_adjustment DOUBLE COMMENT '置信度调整值',
    feedback_timestamp DATETIME COMMENT '用户反馈时间（5分钟窗口内）',
    is_processed BOOLEAN COMMENT '是否已处理到训练数据',
    metadata STRING COMMENT '元数据（JSON格式）'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id, created_at)
DISTRIBUTED BY HASH(system_user_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 设备操作置信度表（扩展原有 device_operations）
-- ============================================
CREATE TABLE IF NOT EXISTS device_operation_confidence (
    id BIGINT NOT NULL COMMENT '主键ID',
    operation_id BIGINT NOT NULL COMMENT '关联的 device_operations.id',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    created_at DATETIME COMMENT '创建时间',
    device_type VARCHAR(50) NOT NULL COMMENT '设备类型',
    action VARCHAR(100) NOT NULL COMMENT '操作动作',
    parameters STRING COMMENT '操作参数（JSON格式）',
    confidence_score DOUBLE NOT NULL COMMENT '置信度分数（0-1）',
    source VARCHAR(50) COMMENT '来源：gmm_prediction, user_feedback, historical_pattern',
    scene_id INT COMMENT '所属场景ID',
    is_user_modified BOOLEAN COMMENT '是否被用户修改过',
    original_confidence DOUBLE COMMENT '原始置信度（修改前）',
    adjustment_reason STRING COMMENT '调整原因'
) ENGINE=OLAP
DUPLICATE KEY(id, operation_id, system_user_id, created_at)
DISTRIBUTED BY HASH(system_user_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 创建视图：结合反馈的增强数据集
-- ============================================
-- 先删除旧视图（如果存在）
DROP VIEW IF EXISTS enhanced_operations_view;

-- 创建新视图
CREATE VIEW enhanced_operations_view AS
SELECT
    o.id,
    o.system_user_id,
    o.created_at,
    o.context_id,
    o.device_type,
    o.device_name,
    o.action,
    o.parameters,
    o.success,
    COALESCE(c.confidence_score, 0.5) as confidence_score,
    COALESCE(c.is_user_modified, FALSE) as is_user_modified,
    COALESCE(c.source, 'historical') as confidence_source,
    -- 时间特征（在数据库端计算）
    HOUR(o.created_at) as hour,
    MINUTE(o.created_at) as minute,
    DAYOFWEEK(o.created_at) as day_of_week,
    CASE WHEN DAYOFWEEK(o.created_at) IN (6, 7) THEN 1 ELSE 0 END as is_weekend,
    CASE WHEN HOUR(o.created_at) >= 6 AND HOUR(o.created_at) < 12 THEN 1 ELSE 0 END as is_morning,
    CASE WHEN HOUR(o.created_at) >= 12 AND HOUR(o.created_at) < 18 THEN 1 ELSE 0 END as is_afternoon,
    CASE WHEN HOUR(o.created_at) >= 18 AND HOUR(o.created_at) < 22 THEN 1 ELSE 0 END as is_evening,
    CASE WHEN HOUR(o.created_at) >= 22 OR HOUR(o.created_at) < 6 THEN 1 ELSE 0 END as is_night
FROM device_operations o
LEFT JOIN device_operation_confidence c ON o.id = c.operation_id
WHERE o.success = TRUE;

-- ============================================
-- 验证表创建
-- ============================================
SELECT '=== 用户反馈表 ===' AS info;
SHOW CREATE TABLE user_feedback;

SELECT '=== 置信度表 ===' AS info;
SHOW CREATE TABLE device_operation_confidence;

SELECT '=== 增强视图 ===' AS info;
SHOW CREATE VIEW enhanced_operations_view;

