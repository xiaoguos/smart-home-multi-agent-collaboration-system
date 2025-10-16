-- 插入模拟设备操作日志数据
-- Insert Simulated Device Operation Log Data

USE smart_home;

-- 生成默认用户的操作日志（综合使用模式，温度偏好25-26度）
INSERT INTO `device_operations` (`user_id`, `device_type`, `device_name`, `device_id`, `action`, `parameters`, `result`, `timestamp`, `success`, `response_time`, `ip_address`, `session_id`) VALUES
-- 最近30天的操作记录
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_temperature', '{"temperature": 26}', '{"status": "success", "new_temperature": 26}', '2024-01-15 19:15:00', 1, 155, '192.168.1.100', 'sess_001'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_temperature', '{"temperature": 25}', '{"status": "success", "new_temperature": 25}', '2024-01-15 21:00:00', 1, 140, '192.168.1.100', 'sess_001'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_power', '{"power": false}', '{"status": "success", "power": false}', '2024-01-15 23:30:00', 1, 95, '192.168.1.100', 'sess_001'),

(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_power', '{"power": true}', '{"status": "success", "power": true}', '2024-01-16 18:00:00', 1, 105, '192.168.1.100', 'sess_002'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_temperature', '{"temperature": 26}', '{"status": "success", "new_temperature": 26}', '2024-01-16 18:30:00', 1, 130, '192.168.1.100', 'sess_002'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_mode', '{"mode": "cool"}', '{"status": "success", "mode": "cool"}', '2024-01-16 19:45:00', 1, 145, '192.168.1.100', 'sess_002'),

(1, 'air_cleaner', '卧室空气净化器', 'AC_BEDROOM_001', 'set_power', '{"power": true}', '{"status": "success", "power": true}', '2024-01-16 20:15:00', 1, 85, '192.168.1.100', 'sess_002'),
(1, 'air_cleaner', '卧室空气净化器', 'AC_BEDROOM_001', 'set_mode', '{"mode": "auto"}', '{"status": "success", "mode": "auto"}', '2024-01-16 20:30:00', 1, 80, '192.168.1.100', 'sess_002'),

-- 更多历史操作记录
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_temperature', '{"temperature": 25}', '{"status": "success", "new_temperature": 25}', '2024-01-14 19:20:00', 1, 150, '192.168.1.100', 'sess_003'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_temperature', '{"temperature": 26}', '{"status": "success", "new_temperature": 26}', '2024-01-14 21:15:00', 1, 135, '192.168.1.100', 'sess_003'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_power', '{"power": false}', '{"status": "success", "power": false}', '2024-01-14 23:00:00', 1, 100, '192.168.1.100', 'sess_003'),

(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_power', '{"power": true}', '{"status": "success", "power": true}', '2024-01-13 18:30:00', 1, 110, '192.168.1.100', 'sess_004'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_temperature', '{"temperature": 26}', '{"status": "success", "new_temperature": 26}', '2024-01-13 19:00:00', 1, 125, '192.168.1.100', 'sess_004'),
(1, 'air_conditioner', '客厅空调', 'AC_LIVING_ROOM_001', 'set_fan_speed', '{"fan_speed": 2}', '{"status": "success", "fan_speed": 2}', '2024-01-13 20:00:00', 1, 120, '192.168.1.100', 'sess_004'),

(1, 'air_cleaner', '卧室空气净化器', 'AC_BEDROOM_001', 'set_power', '{"power": true}', '{"status": "success", "power": true}', '2024-01-13 21:00:00', 1, 90, '192.168.1.100', 'sess_004'),
(1, 'air_cleaner', '卧室空气净化器', 'AC_BEDROOM_001', 'set_mode', '{"mode": "sleep"}', '{"status": "success", "mode": "sleep"}', '2024-01-13 22:00:00', 1, 85, '192.168.1.100', 'sess_004');

-- 添加更多历史数据（过去30天）
-- 这里可以添加更多的历史操作记录来丰富数据挖掘的样本
