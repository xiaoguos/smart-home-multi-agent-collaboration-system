-- 小米账号凭证表
CREATE TABLE IF NOT EXISTS xiaomi_credentials (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    xiaomi_username VARCHAR(100) NOT NULL COMMENT '小米账号',
    service_token VARCHAR(1000) NOT NULL COMMENT '服务令牌',
    ssecurity VARCHAR(255) NOT NULL COMMENT '安全令牌',
    xiaomi_user_id VARCHAR(100) NOT NULL COMMENT '小米用户ID',
    server VARCHAR(10) DEFAULT 'cn' COMMENT '服务器区域',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY(id),
    UNIQUE KEY uk_system_user_id(system_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小米账号凭证表';

