CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;

-- 滴答清单账号凭证表
CREATE TABLE IF NOT EXISTS dida_credentials (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    dida_username VARCHAR(100) NOT NULL COMMENT '滴答清单账号(邮箱)',
    client_id VARCHAR(255) NOT NULL COMMENT '应用Client ID',
    client_secret VARCHAR(255) NOT NULL COMMENT '应用Client Secret',
    access_token VARCHAR(1000) NOT NULL COMMENT '访问令牌',
    refresh_token VARCHAR(1000) NOT NULL COMMENT '刷新令牌',
    token_expires_at DATETIME COMMENT '令牌过期时间',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id)
DISTRIBUTED BY HASH(id) BUCKETS 1
PROPERTIES (
    "replication_num" = "1"
);

