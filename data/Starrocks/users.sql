CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGINT NOT NULL COMMENT '主键ID',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码（加密）',
    email VARCHAR(255) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    nickname VARCHAR(100) COMMENT '昵称',
    avatar VARCHAR(500) COMMENT '头像URL',
    status TINYINT COMMENT '状态：1-正常，0-禁用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间',
    last_login_at DATETIME COMMENT '最后登录时间'
) ENGINE=OLAP
DUPLICATE KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 1
PROPERTIES (
    "replication_num" = "1"
);

-- 插入默认账号（注意：StarRocks DUPLICATE KEY 表允许重复插入）
-- 用户名: admin, 密码: admin123 (SHA256加密后)
-- 用户名: test, 密码: test123 (SHA256加密后)
INSERT INTO users (id, username, password, nickname, status, created_at, updated_at) VALUES 
(1000000001, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '管理员', 1, NOW(), NOW()),
(1000000002, 'test', 'ecd71870d1963316a97e3ac3408c9835ad8cf0f3c1bc703527c30265534f75ae', '测试用户', 1, NOW(), NOW());
