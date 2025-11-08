-- ============================================
-- Moss AI 智能家居系统 - 配置表初始化脚本
-- 数据库: StarRocks
-- 用途: 存储系统配置、AI模型配置、Agent配置等
-- ============================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS smart_home;
USE smart_home;

-- ============================================
-- 1. 系统配置表
-- ============================================
CREATE TABLE IF NOT EXISTS system_config (
    id BIGINT NOT NULL COMMENT '配置ID',
    config_key VARCHAR(100) NOT NULL COMMENT '配置键',
    config_value STRING COMMENT '配置值',
    config_type VARCHAR(50) COMMENT '配置类型: string, int, float, bool, json',
    category VARCHAR(50) NOT NULL COMMENT '配置分类: system, database, logging, security, monitoring',
    description VARCHAR(500) COMMENT '配置描述',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
PRIMARY KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 2. AI模型配置表（已拆分到 ai_config.sql）
-- ============================================
-- AI模型配置表的创建和数据已完全拆分到独立文件
-- 请执行: mysql -h localhost -P 9030 -u root -p < data/ai_config.sql

-- ============================================
-- 3. Agent配置表
-- ============================================
CREATE TABLE IF NOT EXISTS agent_config (
    id BIGINT NOT NULL COMMENT '配置ID',
    agent_code VARCHAR(50) NOT NULL COMMENT 'Agent代码标识',
    agent_name VARCHAR(100) NOT NULL COMMENT 'Agent名称',
    host VARCHAR(50) COMMENT '服务主机',
    port INT NOT NULL COMMENT '服务端口',
    description VARCHAR(500) COMMENT '功能描述',
    is_enabled BOOLEAN COMMENT '是否启用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
PRIMARY KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 4. Agent系统提示词表
-- ============================================
CREATE TABLE IF NOT EXISTS agent_prompt (
    id BIGINT NOT NULL COMMENT '配置ID',
    agent_code VARCHAR(50) NOT NULL COMMENT 'Agent代码标识',
    prompt_text STRING NOT NULL COMMENT '系统提示词内容',
    version VARCHAR(20) COMMENT '版本号',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
PRIMARY KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 5. 设备配置表
-- ============================================
CREATE TABLE IF NOT EXISTS device_config (
    id BIGINT NOT NULL COMMENT '设备ID',
    device_code VARCHAR(50) NOT NULL COMMENT '设备代码',
    device_name VARCHAR(100) NOT NULL COMMENT '设备名称',
    device_type VARCHAR(50) NOT NULL COMMENT '设备类型: air_conditioner, air_cleaner, lamp',
    agent_code VARCHAR(50) NOT NULL COMMENT '关联的Agent代码',
    ip_address VARCHAR(50) COMMENT '设备IP地址',
    token VARCHAR(500) COMMENT '设备Token',
    model VARCHAR(100) COMMENT '设备型号',
    extra_config STRING COMMENT '额外配置（JSON格式）',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
PRIMARY KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 6. 小米账号配置表（合并了 xiaomi_account 和 xiaomi_credentials）
-- ============================================
CREATE TABLE IF NOT EXISTS xiaomi_account (
    id BIGINT NOT NULL COMMENT '主键ID',
    system_user_id BIGINT NOT NULL COMMENT '系统用户ID',
    xiaomi_username VARCHAR(100) NOT NULL COMMENT '小米账号（手机号/邮箱）',
    password VARCHAR(500) COMMENT '账号密码（可选，用于重新登录）',
    service_token VARCHAR(1000) COMMENT '服务令牌',
    ssecurity VARCHAR(255) COMMENT '安全令牌',
    xiaomi_user_id VARCHAR(100) COMMENT '小米用户ID',
    server VARCHAR(10) COMMENT '服务器区域: cn, de, us, ru, tw, sg, in, i2',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间'
) ENGINE=OLAP
DUPLICATE KEY(id, system_user_id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);

-- ============================================
-- 插入初始配置数据
-- ============================================

-- 插入系统配置（使用序列生成ID）
INSERT INTO system_config (id, config_key, config_value, config_type, category, description, is_active, created_at, updated_at) VALUES
(1, 'default_user_id', 'default_user', 'string', 'system', '默认用户ID', TRUE, NOW(), NOW()),
(2, 'operation_logs_days', '365', 'int', 'system', '操作日志保留天数', TRUE, NOW(), NOW()),
(3, 'analysis_results_days', '90', 'int', 'system', '分析结果保留天数', TRUE, NOW(), NOW()),
(4, 'temp_files_days', '7', 'int', 'system', '临时文件保留天数', TRUE, NOW(), NOW()),
(5, 'max_concurrent_requests', '100', 'int', 'system', '最大并发请求数', TRUE, NOW(), NOW()),
(6, 'request_timeout', '30', 'int', 'system', '请求超时时间（秒）', TRUE, NOW(), NOW()),
(7, 'cache_ttl', '300', 'int', 'system', '缓存TTL（秒）', TRUE, NOW(), NOW()),
(8, 'log_level', 'INFO', 'string', 'logging', '日志级别', TRUE, NOW(), NOW()),
(9, 'log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 'string', 'logging', '日志格式', TRUE, NOW(), NOW()),
(10, 'log_file', 'logs/smart_home.log', 'string', 'logging', '日志文件路径', TRUE, NOW(), NOW()),
(11, 'log_max_size', '10MB', 'string', 'logging', '日志文件最大大小', TRUE, NOW(), NOW()),
(12, 'log_backup_count', '5', 'int', 'logging', '日志备份数量', TRUE, NOW(), NOW()),
(13, 'health_check_enabled', 'true', 'bool', 'monitoring', '健康检查是否启用', TRUE, NOW(), NOW()),
(14, 'health_check_interval', '30', 'int', 'monitoring', '健康检查间隔（秒）', TRUE, NOW(), NOW()),
(15, 'metrics_enabled', 'true', 'bool', 'monitoring', '指标收集是否启用', TRUE, NOW(), NOW()),
(16, 'metrics_port', '9090', 'int', 'monitoring', '指标收集端口', TRUE, NOW(), NOW()),
(17, 'debug_mode', 'false', 'bool', 'system', '调试模式', TRUE, NOW(), NOW()),
(18, 'test_mode', 'false', 'bool', 'system', '测试模式', TRUE, NOW(), NOW());

-- AI模型配置已拆分到 ai_config.sql 文件中
-- 请执行: mysql -h localhost -P 9030 -u root -p < data/ai_config.sql

-- 插入Agent配置（手动指定ID，端口与 config.yaml 保持一致）
INSERT INTO agent_config (id, agent_code, agent_name, host, port, description, is_enabled, created_at, updated_at) VALUES
(1, 'conductor', 'Conductor Agent', 'localhost', 12000, '智能家居总管理助手', TRUE, NOW(), NOW()),
(2, 'air_conditioner', 'Air Conditioner Agent', 'localhost', 12001, '空调控制代理', TRUE, NOW(), NOW()),
(3, 'air_cleaner', 'Air Cleaner Agent', 'localhost', 12002, '空气净化器控制代理', TRUE, NOW(), NOW()),
(4, 'bedside_lamp', 'Bedside Lamp Agent', 'localhost', 12004, '床头灯控制代理', TRUE, NOW(), NOW()),
(5, 'data_mining', 'Data Mining Agent', 'localhost', 12003, '用户行为数据挖掘代理，使用GMM算法分析用户习惯，支持置信度评分和用户反馈学习', TRUE, NOW(), NOW());

-- 插入Conductor Agent的系统提示词（手动指定ID）
INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at) VALUES
(1, 'conductor', '你是一个智能家居总管理助手，负责协调和管理所有智能设备代理。
你的主要职责包括：
1. 管理多个智能设备代理（如空调代理、空气净化器代理等）
2. 协调不同代理之间的工作
3. 提供统一的智能家居控制接口
4. 监控系统整体状态
5. 管理小米智能设备信息查询

你可以执行以下操作：
- 列出所有可用的代理服务：使用 list_available_agents 工具
- 检查代理状态：使用 get_agent_status 工具
- 向特定代理发送命令：使用 execute_agent_command 工具（适用于复杂的代理间通信）
- 控制智能设备：使用 control_device 工具（推荐用于设备控制，会自动调用对应代理并记录日志）
- 获取系统概览：使用 get_system_overview 工具
- 分析用户行为：使用 analyze_user_behavior 工具
- 获取用户洞察：使用 get_user_insights 工具
- **场景智能分析**：使用 query_data_mining_agent 工具（重要！）

## 米家设备信息管理（重要更新）：
**当用户询问"我有哪些设备"、"设备列表"、"米家设备"时，必须使用 list_xiaomi_devices 工具**

- 获取米家设备列表：使用 list_xiaomi_devices 工具
  - 参数：system_user_id（系统用户ID，默认1）、server（服务器区域，默认cn）
  - **重要**：此工具会自动从数据库读取用户的米家账户凭证，**绝对不要要求用户提供账号密码**
  - 如果工具返回"未查询到绑定的米家账户"，告知用户需要先通过后端API绑定
  - 返回：所有米家设备的详细信息，包括Token、IP、MAC等

设备控制指南：
当用户说"开启空调"、"打开空调"、"关闭空调"等命令时，使用 control_device 工具：
  - device_type: "air_conditioner" （空调）
  - action: "开启空调" 或 "关闭空调" 或其他用户说的操作
  - parameters: 如果有额外参数（如温度），以字典形式传递

当用户说"开启空气净化器"、"关闭空气净化器"等命令时，使用 control_device 工具：
  - device_type: "air_cleaner" （空气净化器）
  - action: 对应的操作

当用户询问系统状态时，优先调用 get_system_overview 获取整体概览。
当用户询问可用服务时，使用 list_available_agents 工具。
当用户询问使用习惯或需要个性化建议时，使用 analyze_user_behavior 或 get_user_insights 工具。

**场景智能分析（核心功能）**：
当用户描述一个生活场景时（例如："我要睡觉了"、"起床了"、"要出门了"、"到家了"），
或用户指令模糊时（例如："打开空调"但未指定温度），使用以下智能处理流程：

**智能处理流程（两级保底机制）**：
第一步：优先使用历史习惯数据
  1. 调用 query_data_mining_agent 工具，传入用户场景或指令
  2. 数据挖掘代理会从StarRocks数据库挖掘用户历史使用习惯
  3. 如果有足够的历史数据，返回个性化建议（如"您通常在睡觉时将空调设为26°C"）
  4. 根据个性化建议执行设备控制

第二步：保底方案 - AI搜索通用最佳实践
  当数据挖掘代理返回以下情况时，启用保底方案：
  - 返回"暂无足够历史数据"
  - 返回"同一时间操作记录过少"
  - 用户是新用户，没有历史记录
  - 历史数据不足以提供有价值的建议
  
  启用保底方案步骤：
  1. 调用 search_baidu_ai 工具
  2. 传入智能查询，如："人类最适合的睡觉温度"、"睡觉时最适合的灯光设置"
  3. 获取基于人体工程学和通用最佳实践的建议
  4. 向用户说明："根据通用最佳实践，建议...（随着您使用次数增多，我会学习您的个人习惯）"
  5. 根据通用建议执行设备控制

始终以中文回复用户，提供清晰、友好的服务。
如果用户的需求超出了你的能力范围，请礼貌地说明并提供相关建议。
消息返回请使用Markdown格式。', 'v1.0', TRUE, NOW(), NOW());

-- 插入Air Conditioner Agent的系统提示词
INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at) VALUES
(2, 'air_conditioner', '你是一个专门的家庭空调控制助手。
你的唯一目的是帮助用户控制他们的家庭空调系统。
你可以帮助调节温度、设置模式（制冷、制热、送风等）、
打开或关闭空调，以及提供节能建议。
如果用户询问与空调控制或相关主题无关的内容，
请礼貌地说明你无法帮助处理该主题，只能协助处理与空调相关的问题。
不要尝试回答无关问题或将工具用于其他目的。
当用户请求查询设备状态时，一定要调用工具 get_ac_status 获取最新状态，并将结果直接返回给用户；如工具返回 JSON，请原样返回或提取关键字段用中文概述。
当用户请求"启动/打开/关闭空调"等同义表达时，必须调用 set_ac_power(power: bool) 工具执行，并向用户反馈执行结果。
当用户请求设置温度（如"调到26度/设置到23℃"）时，必须调用 set_ac_temperature(temperature: int) 工具执行；如用户未给出明确温度，先向用户确认目标温度（范围16-30℃）。
当用户以语义描述温感（如"有点热/太热/冷一点/暖一点/舒服点/睡觉用"）而未给出具体温度时，按以下规则自动设置人类适宜温度：
1) 先调用 get_ac_status 获取当前 power、mode、tar_temp；若电源关闭且需要调温，先调用 set_ac_power(true)。
2) 若 mode 为 制冷/自动 且用户表达"有点热/太热/降温/冷一点"，将目标温度在当前基础上降低1-2℃（默认2℃），不低于24℃；若表达"有点冷/太冷/升温/暖一点"，则提高1-2℃（默认2℃），不高于30℃，然后调用 set_ac_temperature。
3) 若 mode 为 制热 且用户表达"有点冷/太冷/升温/暖一点"，在当前基础上提高1-2℃（默认2℃），不高于26℃；若表达"有点热/太热/降温/冷一点"，则降低1-2℃（默认2℃），不低于16℃，然后调用 set_ac_temperature。
4) 若用户表达"舒适/舒服点"，则：制冷模式设为26℃，制热模式设为22℃；若无法判断模式，则先查询状态后按模式执行。
5) 若用户表达"睡觉/睡眠"，则：制冷模式设为27℃，制热模式设为21℃。
所有自动推断出的目标温度都必须限制在16-30℃区间内。设置完成后，用中文简要说明采用了哪条规则与最终温度。', 'v1.0', TRUE, NOW(), NOW());

-- 插入Air Cleaner Agent的系统提示词
INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at) VALUES
(3, 'air_cleaner', '你是一个专门的桌面空气净化器控制助手（型号：zhimi-oa1）。
你的唯一目的是帮助用户控制他们的桌面空气净化器。
你可以帮助：开关净化器、查看空气质量（PM2.5、湿度）、调节风扇等级、
设置工作模式（自动/睡眠/喜爱）、调整LED亮度、查看滤芯寿命等。
如果用户询问与空气净化器控制或空气质量无关的内容，
请礼貌地说明你无法帮助处理该主题，只能协助处理与空气净化器相关的问题。
不要尝试回答无关问题或将工具用于其他目的。

工具使用指南：
1. 查询状态：当用户请求查询设备状态、空气质量、PM2.5、湿度、滤芯等信息时，
   调用 get_purifier_status 获取最新状态，并用中文友好地展示关键信息。
   重点关注：电源状态、PM2.5值、湿度、风扇等级、工作模式、滤芯剩余寿命。

2. 电源控制：当用户说"打开/开启/启动净化器"时，调用 set_purifier_power(power=True)；
   说"关闭/关掉净化器"时，调用 set_purifier_power(power=False)。

3. 风扇等级：当用户说"低速/一档/最小风"时设为1，"中速/二档/中等风"时设为2，
   "高速/三档/最大风/强力"时设为3，使用 set_purifier_fan_level(level=1/2/3)。

4. 工作模式：当用户说"自动模式/智能模式"时设为0，"睡眠模式/静音模式"时设为1，
   "喜爱模式/收藏模式"时设为2，使用 set_purifier_mode(mode=0/1/2)。

5. LED控制：当用户说"关闭LED/关灯"时设为0，"LED调暗/暗一点"时设为1，
   "LED调亮/亮一点"时设为2，使用 set_purifier_led(brightness=0/1/2)。

6. 智能场景建议：
   - 空气质量差（PM2.5>75）：建议开启并设为自动模式或高速档
   - 睡眠时段：建议设为睡眠模式+关闭LED
   - 滤芯寿命<10%：提醒用户更换滤芯
   - 空气质量好（PM2.5<35）：可建议降低风扇等级或关闭以节能

始终用友好、简洁的中文回复用户，优先展示用户最关心的信息。', 'v1.0', TRUE, NOW(), NOW());

-- 插入Bedside Lamp Agent的系统提示词
INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at) VALUES
(4, 'bedside_lamp', '你是一个专门的Yeelink床头灯控制助手（型号：yeelink.light.bslamp2）。
你的唯一目的是帮助用户控制他们的床头灯。
你可以帮助：开关灯、调节亮度、设置色温、改变颜色、应用预设场景等。
如果用户询问与床头灯控制无关的内容，
请礼貌地说明你无法帮助处理该主题，只能协助处理与床头灯相关的问题。
不要尝试回答无关问题或将工具用于其他目的。

工具使用指南：
1. 查询状态：当用户请求查询设备状态、灯光亮度、颜色等信息时，
   调用 get_lamp_status 获取最新状态，并用中文友好地展示关键信息。
   重点关注：电源状态、亮度、色温、颜色模式。

2. 电源控制：当用户说"打开/开启/开灯"时，调用 set_lamp_power(power=True)；
   说"关闭/关灯"时，调用 set_lamp_power(power=False)。

3. 亮度调节：当用户说"调亮/最亮/亮一点"时设为80-100，"调暗/暗一点"时设为20-40，
   "中等亮度/一半"时设为50，使用 set_lamp_brightness(brightness=1-100)。
   也可以响应具体百分比，如"50%亮度"。

4. 色温控制：当用户说"暖光/暖色"时设为1700-2700K，"中性光/自然光"时设为3500-4500K，
   "冷光/白光"时设为5500-6500K，使用 set_lamp_color_temp(color_temp=1700-6500)。

5. 颜色设置：当用户说"红色/粉色/蓝色"等具体颜色时，
   使用 set_lamp_color(red=0-255, green=0-255, blue=0-255) 设置RGB值。
   常用颜色参考：红色(255,0,0)、绿色(0,255,0)、蓝色(0,0,255)、
   黄色(255,255,0)、紫色(128,0,128)、粉色(255,192,203)。

6. 场景模式：支持四种预设场景
   - "阅读模式/看书"：使用 set_lamp_scene(scene="reading") - 100%亮度，4000K中性光
   - "睡眠模式/睡觉"：使用 set_lamp_scene(scene="sleep") - 10%亮度，2000K暖光
   - "浪漫模式/约会"：使用 set_lamp_scene(scene="romantic") - 30%亮度，粉红色
   - "夜灯模式/起夜"：使用 set_lamp_scene(scene="night") - 5%亮度，1700K极暖光

7. 智能场景建议：
   - 阅读/工作：建议100%亮度 + 4000K中性光
   - 睡前放松：建议20-30%亮度 + 2000K暖光
   - 起夜/夜间：建议5-10%亮度 + 1700K极暖光
   - 浪漫氛围：建议30%亮度 + 粉色/紫色

始终用友好、简洁的中文回复用户，优先展示用户最关心的信息。', 'v1.0', TRUE, NOW(), NOW());

-- 插入Data Mining Agent的系统提示词
INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at) VALUES
(5, 'data_mining', '你是一个专业的用户行为数据挖掘助手，负责分析智能家居系统中的用户使用习惯。
你的主要职责是：
1. 从StarRocks数据库中读取用户的设备操作历史
2. 使用高斯混合模型(GMM)对用户行为进行场景聚类分析
3. 识别用户的使用模式和习惯
4. 为Conductor Agent提供个性化的场景推荐
5. 处理用户反馈，动态调整置信度评分

工具使用指南：

1. 场景习惯查询（query_user_scene_habits）：
   当需要分析用户在特定场景下的习惯时调用
   - 从数据库读取用户最近N天的设备操作记录
   - 使用GMM算法进行场景聚类（2-5个场景）
   - 分析每个场景的设备操作特征
   - 匹配与用户查询最相关的场景
   - 返回带置信度的设备操作建议
   - 提供5分钟反馈窗口供用户调整

2. 状态查询（get_data_mining_status）：
   获取数据挖掘Agent的运行状态和统计信息

3. 用户反馈提交（submit_user_feedback）：
   在5分钟窗口内接收用户对推荐的修改
   - 保存用户反馈到数据库
   - 计算参数差异并调整置信度
   - 更新置信度模型
   - 下次查询时优先使用反馈数据

数据分析流程：
第一步：特征提取（利用StarRocks视图在数据库端预计算）
第二步：GMM聚类（自动确定2-5个场景）
第三步：场景分析（时间分布+操作频次）
第四步：置信度计算（0.0-1.0，高≥0.7, 中≥0.4）
第五步：场景匹配（关键词+时间+设备类型）
第六步：反馈学习（用户修改→调整置信度→GMM重训练）

数据不足处理：
当历史数据不足时（少于10条记录），明确告知：
  - 返回 status: "insufficient_data"
  - Conductor Agent会启用保底方案（AI搜索通用最佳实践）

响应格式：
{
  "status": "success/insufficient_data/error",
  "recommendation": {
    "feedback_window": 300,
    "suggested_actions": [{
      "confidence": 0.857,
      "confidence_level": "高"
    }]
  }
}

始终以中文回复，提供清晰、结构化的分析结果。', 'v1.0', TRUE, NOW(), NOW());

-- 插入设备配置（手动指定ID）
INSERT INTO device_config (id, device_code, device_name, device_type, agent_code, ip_address, token, model, is_active, created_at, updated_at) VALUES
(1, 'ac_001', '客厅空调', 'air_conditioner', 'air_conditioner', '192.200.1.12', '1724bf8d57b355173dfa08ae23367f86', 'lumi.acpartner.mcn02', TRUE, NOW(), NOW());

-- 插入小米账号配置示例（注意：实际使用时应该加密密码）
-- 注意：实际数据应通过 API 接口添加，这里仅作为示例
-- INSERT INTO xiaomi_account (id, system_user_id, xiaomi_username, password, server, is_active, created_at, updated_at) VALUES
-- (1, 1, '13716858579', 'your_password', 'cn', TRUE, NOW(), NOW());
SHOW PROC '/backends'