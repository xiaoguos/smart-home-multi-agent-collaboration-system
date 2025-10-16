-- 插入设备使用统计数据
-- Insert Device Usage Statistics

USE smart_home;

-- 基于操作日志生成的设备使用统计数据
INSERT INTO `device_usage_stats` (`user_id`, `device_type`, `usage_count`, `total_duration`, `last_used`, `preferred_settings`, `usage_frequency`, `energy_consumption`, `cost_savings`) VALUES
-- 默认用户的使用统计
(1, 'air_conditioner', 48, 1920, '2024-01-16 22:00:00',
 JSON_OBJECT('temperature', 25.5, 'mode', 'cool', 'fan_speed', 2, 'balanced_mode', true),
 'daily', 132.1, 47.5),

(1, 'air_cleaner', 29, 870, '2024-01-16 22:00:00',
 JSON_OBJECT('mode', 'auto', 'smart_mode', true, 'energy_saving', true),
 'daily', 36.2, 12.9);
