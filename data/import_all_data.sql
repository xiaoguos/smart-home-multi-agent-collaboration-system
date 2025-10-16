-- MOSS AI 智能家居系统数据导入脚本
-- Import All Data Script for MOSS AI Smart Home System

-- 设置字符集和时区
SET NAMES utf8mb4;
SET time_zone = '+08:00';
SET FOREIGN_KEY_CHECKS = 0;

-- 显示导入开始信息
SELECT '开始导入MOSS AI智能家居系统数据...' AS 'Status';

-- 1. 创建数据库表结构
SOURCE 01_create_tables.sql;
SELECT '✓ 数据库表结构创建完成' AS 'Status';

-- 2. 插入用户基础数据
SOURCE 02_insert_users.sql;
SELECT '✓ 用户基础数据插入完成' AS 'Status';

-- 3. 插入设备操作日志数据
SOURCE 03_insert_device_operations.sql;
SELECT '✓ 设备操作日志数据插入完成' AS 'Status';

-- 4. 插入环境数据
SOURCE 04_insert_environment_data.sql;
SELECT '✓ 环境数据插入完成' AS 'Status';

-- 5. 插入用户习惯分析数据
SOURCE 05_insert_user_habits.sql;
SELECT '✓ 用户习惯分析数据插入完成' AS 'Status';

-- 6. 插入设备使用统计数据
SOURCE 06_insert_usage_stats.sql;
SELECT '✓ 设备使用统计数据插入完成' AS 'Status';

-- 7. 插入智能场景数据
SOURCE 07_insert_smart_scenes.sql;
SELECT '✓ 智能场景数据插入完成' AS 'Status';

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示数据统计信息
SELECT '数据导入完成！统计信息如下：' AS 'Status';

SELECT 
    'users' AS table_name,
    COUNT(*) AS record_count
FROM users
UNION ALL
SELECT 
    'devices' AS table_name,
    COUNT(*) AS record_count
FROM devices
UNION ALL
SELECT 
    'device_operations' AS table_name,
    COUNT(*) AS record_count
FROM device_operations
UNION ALL
SELECT 
    'environment_data' AS table_name,
    COUNT(*) AS record_count
FROM environment_data
UNION ALL
SELECT 
    'user_habits' AS table_name,
    COUNT(*) AS record_count
FROM user_habits
UNION ALL
SELECT 
    'device_usage_stats' AS table_name,
    COUNT(*) AS record_count
FROM device_usage_stats
UNION ALL
SELECT 
    'smart_scenes' AS table_name,
    COUNT(*) AS record_count
FROM smart_scenes;

-- 显示用户使用习惯摘要
SELECT '用户使用习惯摘要：' AS 'Status';

SELECT 
    u.username,
    u.nickname,
    COUNT(do.id) AS total_operations,
    AVG(JSON_EXTRACT(do.parameters, '$.temperature')) AS avg_temperature,
    COUNT(DISTINCT DATE(do.timestamp)) AS active_days
FROM users u
LEFT JOIN device_operations do ON u.id = do.user_id
WHERE do.device_type = 'air_conditioner'
GROUP BY u.id, u.username, u.nickname
ORDER BY total_operations DESC;

-- 显示设备使用统计
SELECT '设备使用统计：' AS 'Status';

SELECT 
    device_type,
    COUNT(*) AS device_count,
    SUM(usage_count) AS total_usage,
    AVG(usage_count) AS avg_usage_per_device
FROM device_usage_stats
GROUP BY device_type;

-- 显示智能场景统计
SELECT '智能场景统计：' AS 'Status';

SELECT 
    scene_type,
    COUNT(*) AS scene_count,
    SUM(execution_count) AS total_executions,
    AVG(execution_count) AS avg_executions_per_scene
FROM smart_scenes
GROUP BY scene_type;

SELECT '所有数据导入完成！MOSS AI智能家居系统已准备就绪。' AS 'Status';
