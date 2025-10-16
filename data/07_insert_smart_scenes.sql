-- 插入智能场景数据
-- Insert Smart Scenes Data

USE smart_home;

-- 基于用户习惯生成的智能场景
INSERT INTO `smart_scenes` (`user_id`, `scene_name`, `scene_type`, `description`, `trigger_conditions`, `actions`, `is_active`, `execution_count`, `last_executed`) VALUES
-- 默认用户的智能场景
(1, '标准晚间模式', 'standard', '晚上7点开启空调，设置标准温度',
 JSON_OBJECT('time', '19:00', 'weekdays', true, 'temperature_threshold', 28),
 JSON_OBJECT('air_conditioner', JSON_OBJECT('power', true, 'temperature', 26, 'mode', 'cool', 'fan_speed', 2)),
 1, 17, '2024-01-16 19:00:00'),

(1, '智能空气管理', 'air_management', '根据空气质量自动管理空气净化器',
 JSON_OBJECT('air_quality_threshold', 85, 'auto_management', true, 'time_range', JSON_ARRAY('18:00', '23:00')),
 JSON_OBJECT('air_cleaner', JSON_OBJECT('power', true, 'mode', 'auto', 'smart_monitoring', true)),
 1, 19, '2024-01-16 20:15:00'),

(1, '睡眠模式', 'sleep', '晚上11点自动关闭空调，开启空气净化器睡眠模式',
 JSON_OBJECT('time', '23:00', 'weekdays', true, 'user_presence', true),
 JSON_OBJECT('air_conditioner', JSON_OBJECT('power', false), 'air_cleaner', JSON_OBJECT('mode', 'sleep')),
 1, 12, '2024-01-16 23:00:00'),

(1, '智能舒适优化', 'comfort_optimization', '根据环境自动调整空调设置',
 JSON_OBJECT('temperature_threshold', 30, 'humidity_threshold', 70, 'auto_adjustment', true),
 JSON_OBJECT('air_conditioner', JSON_OBJECT('power', true, 'temperature', 26, 'mode', 'auto', 'fan_speed', 2)),
 1, 15, '2024-01-16 18:00:00');
