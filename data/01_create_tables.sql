-- MOSS AI 智能家居系统数据库表结构
-- Database Schema for MOSS AI Smart Home System

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS smart_home DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_home;

-- 1. 用户表
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '头像URL',
  `preferences` json DEFAULT NULL COMMENT '用户偏好设置',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 2. 设备操作日志表
DROP TABLE IF EXISTS `device_operations`;
CREATE TABLE `device_operations` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '操作ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `device_type` varchar(50) NOT NULL COMMENT '设备类型',
  `device_name` varchar(100) NOT NULL COMMENT '设备名称',
  `device_id` varchar(100) DEFAULT NULL COMMENT '设备唯一标识',
  `action` varchar(50) NOT NULL COMMENT '操作类型',
  `parameters` json DEFAULT NULL COMMENT '操作参数',
  `result` json DEFAULT NULL COMMENT '操作结果',
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `success` tinyint(1) DEFAULT '1' COMMENT '是否成功',
  `response_time` int DEFAULT NULL COMMENT '响应时间(毫秒)',
  `ip_address` varchar(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` varchar(500) DEFAULT NULL COMMENT '用户代理',
  `session_id` varchar(100) DEFAULT NULL COMMENT '会话ID',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_device_type` (`device_type`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_action` (`action`),
  KEY `idx_success` (`success`),
  CONSTRAINT `fk_device_ops_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备操作日志表';

-- 3. 用户习惯分析表
DROP TABLE IF EXISTS `user_habits`;
CREATE TABLE `user_habits` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '习惯ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `habit_type` varchar(50) NOT NULL COMMENT '习惯类型',
  `pattern_data` json NOT NULL COMMENT '模式数据',
  `confidence_score` decimal(5,2) DEFAULT '0.00' COMMENT '置信度分数',
  `frequency` varchar(20) DEFAULT NULL COMMENT '频率',
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_habit_type` (`habit_type`),
  KEY `idx_confidence` (`confidence_score`),
  CONSTRAINT `fk_habits_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户习惯分析表';

-- 4. 设备使用统计表
DROP TABLE IF EXISTS `device_usage_stats`;
CREATE TABLE `device_usage_stats` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '统计ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `device_type` varchar(50) NOT NULL COMMENT '设备类型',
  `usage_count` int DEFAULT '0' COMMENT '使用次数',
  `total_duration` int DEFAULT '0' COMMENT '总使用时长(分钟)',
  `last_used` datetime DEFAULT NULL COMMENT '最后使用时间',
  `preferred_settings` json DEFAULT NULL COMMENT '偏好设置',
  `usage_frequency` varchar(20) DEFAULT NULL COMMENT '使用频率',
  `energy_consumption` decimal(10,2) DEFAULT '0.00' COMMENT '能耗统计',
  `cost_savings` decimal(10,2) DEFAULT '0.00' COMMENT '节省成本',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_device` (`user_id`, `device_type`),
  KEY `idx_usage_count` (`usage_count`),
  KEY `idx_last_used` (`last_used`),
  CONSTRAINT `fk_usage_stats_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备使用统计表';

-- 5. 智能场景表
DROP TABLE IF EXISTS `smart_scenes`;
CREATE TABLE `smart_scenes` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '场景ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `scene_name` varchar(100) NOT NULL COMMENT '场景名称',
  `scene_type` varchar(50) NOT NULL COMMENT '场景类型',
  `description` text COMMENT '场景描述',
  `trigger_conditions` json NOT NULL COMMENT '触发条件',
  `actions` json NOT NULL COMMENT '执行动作',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  `execution_count` int DEFAULT '0' COMMENT '执行次数',
  `last_executed` datetime DEFAULT NULL COMMENT '最后执行时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_scene_type` (`scene_type`),
  KEY `idx_is_active` (`is_active`),
  CONSTRAINT `fk_scenes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='智能场景表';

-- 6. 环境数据表
DROP TABLE IF EXISTS `environment_data`;
CREATE TABLE `environment_data` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '数据ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `temperature` decimal(5,2) DEFAULT NULL COMMENT '温度(°C)',
  `humidity` decimal(5,2) DEFAULT NULL COMMENT '湿度(%)',
  `air_quality` int DEFAULT NULL COMMENT '空气质量指数',
  `pm25` decimal(8,2) DEFAULT NULL COMMENT 'PM2.5浓度',
  `pm10` decimal(8,2) DEFAULT NULL COMMENT 'PM10浓度',
  `co2` decimal(8,2) DEFAULT NULL COMMENT 'CO2浓度(ppm)',
  `light_level` int DEFAULT NULL COMMENT '光照强度(lux)',
  `noise_level` int DEFAULT NULL COMMENT '噪音水平(dB)',
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  `location` varchar(100) DEFAULT NULL COMMENT '位置信息',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_temperature` (`temperature`),
  KEY `idx_air_quality` (`air_quality`),
  CONSTRAINT `fk_env_data_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='环境数据表';

-- 7. 系统日志表
DROP TABLE IF EXISTS `system_logs`;
CREATE TABLE `system_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `level` varchar(20) NOT NULL COMMENT '日志级别',
  `module` varchar(50) NOT NULL COMMENT '模块名称',
  `message` text NOT NULL COMMENT '日志消息',
  `details` json DEFAULT NULL COMMENT '详细信息',
  `user_id` bigint DEFAULT NULL COMMENT '用户ID',
  `ip_address` varchar(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` varchar(500) DEFAULT NULL COMMENT '用户代理',
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
  PRIMARY KEY (`id`),
  KEY `idx_level` (`level`),
  KEY `idx_module` (`module`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- 8. 设备信息表
DROP TABLE IF EXISTS `devices`;
CREATE TABLE `devices` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `device_type` varchar(50) NOT NULL COMMENT '设备类型',
  `device_name` varchar(100) NOT NULL COMMENT '设备名称',
  `device_id` varchar(100) NOT NULL COMMENT '设备唯一标识',
  `brand` varchar(50) DEFAULT NULL COMMENT '品牌',
  `model` varchar(100) DEFAULT NULL COMMENT '型号',
  `ip_address` varchar(45) DEFAULT NULL COMMENT 'IP地址',
  `mac_address` varchar(17) DEFAULT NULL COMMENT 'MAC地址',
  `status` varchar(20) DEFAULT 'offline' COMMENT '设备状态',
  `capabilities` json DEFAULT NULL COMMENT '设备能力',
  `settings` json DEFAULT NULL COMMENT '设备设置',
  `last_seen` datetime DEFAULT NULL COMMENT '最后在线时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_device_id` (`device_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_device_type` (`device_type`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_devices_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备信息表';

SET FOREIGN_KEY_CHECKS = 1;
