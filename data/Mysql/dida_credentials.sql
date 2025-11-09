CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;

-- 滴答清单账号凭证表（MySQL版本）
CREATE TABLE IF NOT EXISTS dida_credentials (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    dida_username VARCHAR(100) NOT NULL COMMENT '滴答清单账号(邮箱)',
    client_id VARCHAR(255) NOT NULL COMMENT '应用Client ID',
    client_secret VARCHAR(255) NOT NULL COMMENT '应用Client Secret',
    access_token VARCHAR(1000) NOT NULL COMMENT '访问令牌',
    refresh_token VARCHAR(1000) NOT NULL COMMENT '刷新令牌',
    token_expires_at DATETIME COMMENT '令牌过期时间',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活(1=激活,0=未激活)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_system_user_id (system_user_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='滴答清单账号凭证表';

