-- =====================================================
-- 测试数据：设备操作记录
-- 用于演示数据挖掘 Agent 的场景聚类功能
-- =====================================================

-- 使用数据库
USE smart_home;

-- 清空现有测试数据（可选，谨慎使用）
-- TRUNCATE TABLE device_operations;

-- =====================================================
-- 场景1：早上起床场景 (6:30-8:00)
-- 习惯：开灯 -> 开空调 -> 开空气净化器
-- =====================================================

-- 第1天早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000001, 1000000001, '2024-11-01 06:45:00', 'morning-1', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 60, "color_temp": 4000}', TRUE, '床头灯已开启', NULL, 350),
(1730000000002, 1000000001, '2024-11-01 06:46:00', 'morning-1', 'air_conditioner', '空调', 'turn_on', '{"temperature": 24, "mode": "cool"}', TRUE, '空调已开启', NULL, 450),
(1730000000003, 1000000001, '2024-11-01 06:47:00', 'morning-1', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 2}', TRUE, '空气净化器已开启', NULL, 380);

-- 第2天早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000011, 1000000001, '2024-11-02 06:50:00', 'morning-2', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 65, "color_temp": 4000}', TRUE, '床头灯已开启', NULL, 340),
(1730000000012, 1000000001, '2024-11-02 06:51:00', 'morning-2', 'air_conditioner', '空调', 'turn_on', '{"temperature": 23, "mode": "cool"}', TRUE, '空调已开启', NULL, 460),
(1730000000013, 1000000001, '2024-11-02 06:52:00', 'morning-2', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 2}', TRUE, '空气净化器已开启', NULL, 370);

-- 第3天早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000021, 1000000001, '2024-11-03 07:00:00', 'morning-3', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 70, "color_temp": 4200}', TRUE, '床头灯已开启', NULL, 355),
(1730000000022, 1000000001, '2024-11-03 07:01:00', 'morning-3', 'air_conditioner', '空调', 'turn_on', '{"temperature": 24, "mode": "cool"}', TRUE, '空调已开启', NULL, 445),
(1730000000023, 1000000001, '2024-11-03 07:02:00', 'morning-3', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 3}', TRUE, '空气净化器已开启', NULL, 390);

-- 第4天早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000031, 1000000001, '2024-11-04 06:55:00', 'morning-4', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 60, "color_temp": 4000}', TRUE, '床头灯已开启', NULL, 345),
(1730000000032, 1000000001, '2024-11-04 06:56:00', 'morning-4', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 455),
(1730000000033, 1000000001, '2024-11-04 06:57:00', 'morning-4', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 2}', TRUE, '空气净化器已开启', NULL, 375);

-- 第5天早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000041, 1000000001, '2024-11-05 07:10:00', 'morning-5', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 65, "color_temp": 4100}', TRUE, '床头灯已开启', NULL, 360),
(1730000000042, 1000000001, '2024-11-05 07:11:00', 'morning-5', 'air_conditioner', '空调', 'turn_on', '{"temperature": 24, "mode": "cool"}', TRUE, '空调已开启', NULL, 450),
(1730000000043, 1000000001, '2024-11-05 07:12:00', 'morning-5', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 2}', TRUE, '空气净化器已开启', NULL, 380);


-- =====================================================
-- 场景2：下午回家场景 (17:00-18:30)
-- 习惯：开空气净化器 -> 开空调
-- =====================================================

-- 第1天下午
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000101, 1000000001, '2024-11-01 17:30:00', 'afternoon-1', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 3}', TRUE, '空气净化器已开启', NULL, 390),
(1730000000102, 1000000001, '2024-11-01 17:32:00', 'afternoon-1', 'air_conditioner', '空调', 'turn_on', '{"temperature": 26, "mode": "cool"}', TRUE, '空调已开启', NULL, 470);

-- 第2天下午
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000111, 1000000001, '2024-11-02 17:25:00', 'afternoon-2', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 3}', TRUE, '空气净化器已开启', NULL, 385),
(1730000000112, 1000000001, '2024-11-02 17:27:00', 'afternoon-2', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 465);

-- 第3天下午
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000121, 1000000001, '2024-11-03 17:40:00', 'afternoon-3', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 3}', TRUE, '空气净化器已开启', NULL, 395),
(1730000000122, 1000000001, '2024-11-03 17:42:00', 'afternoon-3', 'air_conditioner', '空调', 'turn_on', '{"temperature": 26, "mode": "cool"}', TRUE, '空调已开启', NULL, 480);

-- 第4天下午
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000131, 1000000001, '2024-11-04 17:35:00', 'afternoon-4', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 3}', TRUE, '空气净化器已开启', NULL, 388),
(1730000000132, 1000000001, '2024-11-04 17:37:00', 'afternoon-4', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 475);

-- 第5天下午
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000141, 1000000001, '2024-11-05 17:20:00', 'afternoon-5', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 3}', TRUE, '空气净化器已开启', NULL, 392),
(1730000000142, 1000000001, '2024-11-05 17:22:00', 'afternoon-5', 'air_conditioner', '空调', 'turn_on', '{"temperature": 26, "mode": "cool"}', TRUE, '空调已开启', NULL, 478);


-- =====================================================
-- 场景3：晚上回家场景 (19:00-20:30)
-- 习惯：开床头灯 -> 开空调 -> 开空气净化器
-- =====================================================

-- 第1天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000201, 1000000001, '2024-11-01 19:15:00', 'evening-1', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 80, "color_temp": 3000}', TRUE, '床头灯已开启', NULL, 365),
(1730000000202, 1000000001, '2024-11-01 19:16:00', 'evening-1', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 485),
(1730000000203, 1000000001, '2024-11-01 19:17:00', 'evening-1', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 395);

-- 第2天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000211, 1000000001, '2024-11-02 19:20:00', 'evening-2', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 75, "color_temp": 2900}', TRUE, '床头灯已开启', NULL, 358),
(1730000000212, 1000000001, '2024-11-02 19:21:00', 'evening-2', 'air_conditioner', '空调', 'turn_on', '{"temperature": 26, "mode": "cool"}', TRUE, '空调已开启', NULL, 490),
(1730000000213, 1000000001, '2024-11-02 19:22:00', 'evening-2', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 390);

-- 第3天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000221, 1000000001, '2024-11-03 19:10:00', 'evening-3', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 80, "color_temp": 3000}', TRUE, '床头灯已开启', NULL, 362),
(1730000000222, 1000000001, '2024-11-03 19:11:00', 'evening-3', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 488),
(1730000000223, 1000000001, '2024-11-03 19:12:00', 'evening-3', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 392);

-- 第4天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000231, 1000000001, '2024-11-04 19:25:00', 'evening-4', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 78, "color_temp": 2950}', TRUE, '床头灯已开启', NULL, 368),
(1730000000232, 1000000001, '2024-11-04 19:26:00', 'evening-4', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 486),
(1730000000233, 1000000001, '2024-11-04 19:27:00', 'evening-4', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 394);

-- 第5天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000241, 1000000001, '2024-11-05 19:18:00', 'evening-5', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 82, "color_temp": 3100}', TRUE, '床头灯已开启', NULL, 360),
(1730000000242, 1000000001, '2024-11-05 19:19:00', 'evening-5', 'air_conditioner', '空调', 'turn_on', '{"temperature": 26, "mode": "cool"}', TRUE, '空调已开启', NULL, 492),
(1730000000243, 1000000001, '2024-11-05 19:20:00', 'evening-5', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 388);

-- 第6天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000251, 1000000001, '2024-11-06 19:22:00', 'evening-6', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 80, "color_temp": 3000}', TRUE, '床头灯已开启', NULL, 364),
(1730000000252, 1000000001, '2024-11-06 19:23:00', 'evening-6', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 487),
(1730000000253, 1000000001, '2024-11-06 19:24:00', 'evening-6', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 391);

-- 第7天晚上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000261, 1000000001, '2024-11-07 19:12:00', 'evening-7', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 75, "color_temp": 2950}', TRUE, '床头灯已开启', NULL, 366),
(1730000000262, 1000000001, '2024-11-07 19:13:00', 'evening-7', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 489),
(1730000000263, 1000000001, '2024-11-07 19:14:00', 'evening-7', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "sleep", "fan_level": 1}', TRUE, '空气净化器已开启', NULL, 393);


-- =====================================================
-- 场景4：睡前场景 (22:00-23:30)
-- 习惯：调暗床头灯 -> 调低空调温度 -> 空气净化器睡眠模式
-- =====================================================

-- 第1天睡前
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000301, 1000000001, '2024-11-01 22:30:00', 'night-1', 'bedside_lamp', '床头灯', 'set_brightness', '{"brightness": 30}', TRUE, '亮度已调整', NULL, 320),
(1730000000302, 1000000001, '2024-11-01 22:31:00', 'night-1', 'air_conditioner', '空调', 'set_temperature', '{"temperature": 27}', TRUE, '温度已调整', NULL, 410),
(1730000000303, 1000000001, '2024-11-01 22:32:00', 'night-1', 'air_cleaner', '空气净化器', 'set_mode', '{"mode": "sleep", "fan_level": 1}', TRUE, '模式已切换', NULL, 350);

-- 第2天睡前
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000311, 1000000001, '2024-11-02 22:25:00', 'night-2', 'bedside_lamp', '床头灯', 'set_brightness', '{"brightness": 25}', TRUE, '亮度已调整', NULL, 315),
(1730000000312, 1000000001, '2024-11-02 22:26:00', 'night-2', 'air_conditioner', '空调', 'set_temperature', '{"temperature": 27}', TRUE, '温度已调整', NULL, 415),
(1730000000313, 1000000001, '2024-11-02 22:27:00', 'night-2', 'air_cleaner', '空气净化器', 'set_mode', '{"mode": "sleep", "fan_level": 1}', TRUE, '模式已切换', NULL, 348);

-- 第3天睡前
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000321, 1000000001, '2024-11-03 22:40:00', 'night-3', 'bedside_lamp', '床头灯', 'set_brightness', '{"brightness": 30}', TRUE, '亮度已调整', NULL, 318),
(1730000000322, 1000000001, '2024-11-03 22:41:00', 'night-3', 'air_conditioner', '空调', 'set_temperature', '{"temperature": 28}', TRUE, '温度已调整', NULL, 412),
(1730000000323, 1000000001, '2024-11-03 22:42:00', 'night-3', 'air_cleaner', '空气净化器', 'set_mode', '{"mode": "sleep", "fan_level": 1}', TRUE, '模式已切换', NULL, 352);

-- 第4天睡前
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000331, 1000000001, '2024-11-04 22:35:00', 'night-4', 'bedside_lamp', '床头灯', 'set_brightness', '{"brightness": 28}', TRUE, '亮度已调整', NULL, 322),
(1730000000332, 1000000001, '2024-11-04 22:36:00', 'night-4', 'air_conditioner', '空调', 'set_temperature', '{"temperature": 27}', TRUE, '温度已调整', NULL, 408),
(1730000000333, 1000000001, '2024-11-04 22:37:00', 'night-4', 'air_cleaner', '空气净化器', 'set_mode', '{"mode": "sleep", "fan_level": 1}', TRUE, '模式已切换', NULL, 345);

-- 第5天睡前
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000341, 1000000001, '2024-11-05 22:28:00', 'night-5', 'bedside_lamp', '床头灯', 'set_brightness', '{"brightness": 30}', TRUE, '亮度已调整', NULL, 325),
(1730000000342, 1000000001, '2024-11-05 22:29:00', 'night-5', 'air_conditioner', '空调', 'set_temperature', '{"temperature": 27}', TRUE, '温度已调整', NULL, 418),
(1730000000343, 1000000001, '2024-11-05 22:30:00', 'night-5', 'air_cleaner', '空气净化器', 'set_mode', '{"mode": "sleep", "fan_level": 1}', TRUE, '模式已切换', NULL, 355);


-- =====================================================
-- 场景5：周末早上场景 (9:00-10:30)
-- 习惯：比平时晚起，开灯亮度较低
-- =====================================================

-- 周六早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000401, 1000000001, '2024-11-02 09:30:00', 'weekend-1', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 50, "color_temp": 3500}', TRUE, '床头灯已开启', NULL, 342),
(1730000000402, 1000000001, '2024-11-02 09:32:00', 'weekend-1', 'air_conditioner', '空调', 'turn_on', '{"temperature": 26, "mode": "cool"}', TRUE, '空调已开启', NULL, 462),
(1730000000403, 1000000001, '2024-11-02 09:35:00', 'weekend-1', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 2}', TRUE, '空气净化器已开启', NULL, 372);

-- 周日早上
INSERT INTO device_operations (id, system_user_id, created_at, context_id, device_type, device_name, action, parameters, success, response, error_message, execution_time) VALUES
(1730000000411, 1000000001, '2024-11-03 09:45:00', 'weekend-2', 'bedside_lamp', '床头灯', 'turn_on', '{"brightness": 55, "color_temp": 3600}', TRUE, '床头灯已开启', NULL, 338),
(1730000000412, 1000000001, '2024-11-03 09:47:00', 'weekend-2', 'air_conditioner', '空调', 'turn_on', '{"temperature": 25, "mode": "cool"}', TRUE, '空调已开启', NULL, 458),
(1730000000413, 1000000001, '2024-11-03 09:50:00', 'weekend-2', 'air_cleaner', '空气净化器', 'turn_on', '{"mode": "auto", "fan_level": 2}', TRUE, '空气净化器已开启', NULL, 368);


-- =====================================================
-- 统计信息
-- =====================================================

-- 查询插入的数据统计
SELECT 
    '插入完成！数据统计：' as message,
    COUNT(*) as total_records,
    COUNT(DISTINCT DATE(created_at)) as days_covered,
    COUNT(DISTINCT device_type) as device_types,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM device_operations
WHERE system_user_id = 1000000001;

-- 按时间段统计
SELECT 
    CASE 
        WHEN HOUR(created_at) >= 6 AND HOUR(created_at) < 12 THEN '早上 (6-12点)'
        WHEN HOUR(created_at) >= 12 AND HOUR(created_at) < 18 THEN '下午 (12-18点)'
        WHEN HOUR(created_at) >= 18 AND HOUR(created_at) < 22 THEN '晚上 (18-22点)'
        ELSE '夜晚 (22-6点)'
    END as time_period,
    COUNT(*) as operation_count
FROM device_operations
WHERE system_user_id = 1000000001
GROUP BY 
    CASE 
        WHEN HOUR(created_at) >= 6 AND HOUR(created_at) < 12 THEN '早上 (6-12点)'
        WHEN HOUR(created_at) >= 12 AND HOUR(created_at) < 18 THEN '下午 (12-18点)'
        WHEN HOUR(created_at) >= 18 AND HOUR(created_at) < 22 THEN '晚上 (18-22点)'
        ELSE '夜晚 (22-6点)'
    END
ORDER BY operation_count DESC;

-- 按设备类型统计
SELECT 
    device_type,
    device_name,
    COUNT(*) as operation_count,
    COUNT(DISTINCT action) as unique_actions
FROM device_operations
WHERE system_user_id = 1000000001
GROUP BY device_type, device_name
ORDER BY operation_count DESC;

