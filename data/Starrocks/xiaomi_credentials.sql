CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;
-- 小米账号凭证表
CREATE TABLE IF NOT EXISTS xiaomi_credentials (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    xiaomi_username VARCHAR(100) NOT NULL COMMENT '小米账号',
    service_token VARCHAR(1000) NOT NULL COMMENT '服务令牌',
    ssecurity VARCHAR(255) NOT NULL COMMENT '安全令牌',
    xiaomi_user_id VARCHAR(100) NOT NULL COMMENT '小米用户ID',
    server VARCHAR(10) COMMENT '服务器区域',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id)
DISTRIBUTED BY HASH(id) BUCKETS 1
PROPERTIES (
    "replication_num" = "1"
);

