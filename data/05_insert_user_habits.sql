-- 插入用户习惯分析数据
-- Insert User Habits Analysis Data

USE smart_home;

-- 基于操作日志分析生成的用户习惯数据
INSERT INTO `user_habits` (`user_id`, `habit_type`, `pattern_data`, `confidence_score`, `frequency`, `is_active`) VALUES
-- 默认用户的习惯分析
(1, 'temperature_preference', 
 JSON_OBJECT(
   'preferred_temperature', 25.5,
   'temperature_range', JSON_ARRAY(25, 26),
   'most_common_temperature', 26,
   'average_temperature', 25.5,
   'temperature_variance', 0.5
 ), 0.84, 'daily', 1),

(1, 'usage_time_pattern',
 JSON_OBJECT(
   'peak_hours', JSON_ARRAY(19, 20, 21),
   'usage_start_time', '18:00',
   'usage_end_time', '23:30',
   'most_active_hour', 20,
   'standard_evening_usage', true
 ), 0.86, 'daily', 1),

(1, 'device_usage_frequency',
 JSON_OBJECT(
   'air_conditioner_usage', 'high',
   'air_cleaner_usage', 'medium',
   'daily_operations', 3.2,
   'weekly_operations', 22.4,
   'preferred_device', 'air_conditioner'
 ), 0.88, 'daily', 1),

(1, 'energy_saving_behavior',
 JSON_OBJECT(
   'auto_shutdown', true,
   'temperature_adjustment_frequency', 'low',
   'night_mode_usage', true,
   'energy_efficiency_score', 7.8
 ), 0.76, 'daily', 1),

(1, 'comfort_optimization',
 JSON_OBJECT(
   'fan_speed_adjustment', 'occasional',
   'mode_switching', 'occasional',
   'comfort_score', 8.0,
   'optimization_frequency', 'moderate'
 ), 0.78, 'daily', 1),

(1, 'balanced_usage_pattern',
 JSON_OBJECT(
   'device_balance', 'good',
   'usage_efficiency', 'moderate',
   'multi_device_coordination', true,
   'smart_scheduling', true
 ), 0.81, 'daily', 1);
