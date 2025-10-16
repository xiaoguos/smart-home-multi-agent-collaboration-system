-- 插入基础用户数据
-- Insert Basic User Data

USE smart_home;

-- 插入默认用户
INSERT INTO `users` (`username`, `email`, `phone`, `nickname`, `avatar`, `preferences`, `is_active`) VALUES
('default_user', 'user@example.com', '13800138000', '智能家居用户', 'https://example.com/avatars/default.jpg',
 JSON_OBJECT(
   'language', 'zh-CN',
   'timezone', 'Asia/Shanghai',
   'temperature_unit', 'celsius',
   'notifications', JSON_OBJECT('email', true, 'sms', false, 'push', true),
   'privacy', JSON_OBJECT('data_sharing', true, 'analytics', true)
 ), 1);

-- 插入设备信息
INSERT INTO `devices` (`user_id`, `device_type`, `device_name`, `device_id`, `brand`, `model`, `ip_address`, `mac_address`, `status`, `capabilities`, `settings`) VALUES
-- 默认用户的设备
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', '格力', 'KFR-35GW', '192.168.1.101', 'AA:BB:CC:DD:EE:01', 'online',
 JSON_OBJECT('temperature_range', JSON_ARRAY(16, 30), 'modes', JSON_ARRAY('cool', 'heat', 'fan', 'auto'), 'fan_speeds', JSON_ARRAY(1, 2, 3, 4)),
 JSON_OBJECT('current_temperature', 25, 'target_temperature', 26, 'mode', 'cool', 'fan_speed', 2)),

(1, 'air_cleaner', '卧室空气净化器', 'AC_BEDROOM_001', '小米', 'Mi Air Purifier 3', '192.168.1.102', 'AA:BB:CC:DD:EE:02', 'online',
 JSON_OBJECT('purification_modes', JSON_ARRAY('auto', 'sleep', 'favorite', 'high'), 'filter_types', JSON_ARRAY('HEPA', 'activated_carbon')),
 JSON_OBJECT('current_mode', 'auto', 'air_quality', 45, 'filter_life', 85));
