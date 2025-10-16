# MOSS AI 智能家居系统数据文件

本目录包含MOSS AI智能家居系统的数据库结构和模拟数据，用于支持数据挖掘代理分析用户习惯。

## 📁 文件结构

```
data/
├── 01_create_tables.sql      # 数据库表结构
├── 02_insert_users.sql       # 用户基础数据
├── 03_insert_device_operations.sql  # 设备操作日志
├── 04_insert_environment_data.sql   # 环境数据
├── 05_insert_user_habits.sql        # 用户习惯分析
├── 06_insert_usage_stats.sql        # 设备使用统计
├── 07_insert_smart_scenes.sql       # 智能场景数据
├── import_all_data.sql       # 一键导入脚本
└── README.md                 # 本文件
```

## 🗄️ 数据库表结构

### 核心表

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `users` | 用户表 | id, username, email, preferences |
| `devices` | 设备信息表 | device_type, device_name, capabilities |
| `device_operations` | 设备操作日志 | user_id, action, parameters, timestamp |
| `environment_data` | 环境数据 | temperature, humidity, air_quality |
| `user_habits` | 用户习惯分析 | habit_type, pattern_data, confidence_score |
| `device_usage_stats` | 设备使用统计 | usage_count, total_duration, energy_consumption |
| `smart_scenes` | 智能场景 | scene_name, trigger_conditions, actions |
| `system_logs` | 系统日志 | level, module, message, timestamp |

## 👥 模拟用户数据

### 用户档案

**默认用户** - 智能家居用户
- 使用时间：晚上7-11点
- 温度偏好：25-26°C
- 设备：客厅空调 + 卧室空气净化器
- 使用习惯：标准晚间使用模式，注重节能和舒适平衡

## 📊 数据挖掘场景

### 用户行为分析

1. **使用时间模式**
   - 分析用户在不同时间段的设备使用习惯
   - 识别高峰使用时间和使用频率

2. **温度偏好分析**
   - 统计用户偏好的温度范围
   - 分析温度调整的频率和模式

3. **设备使用频率**
   - 统计不同设备的使用次数和时长
   - 分析设备间的使用关联性

4. **节能行为分析**
   - 分析用户的节能意识和行为
   - 统计自动关机等节能操作

### 智能推荐场景

1. **个性化温度推荐**
   - 基于历史数据推荐最佳温度设置
   - 考虑时间、季节、环境因素

2. **使用时间预测**
   - 预测用户可能的设备使用时间
   - 提前准备设备状态

3. **节能建议**
   - 基于使用模式提供节能建议
   - 推荐最优的设备配置

4. **场景自动化**
   - 根据用户习惯自动创建智能场景
   - 优化场景触发条件和执行动作

## 🚀 使用方法

### 1. 导入所有数据

```bash
# 使用一键导入脚本
mysql -u root -p smart_home < import_all_data.sql
```

### 2. 分步导入

```bash
# 1. 创建表结构
mysql -u root -p smart_home < 01_create_tables.sql

# 2. 导入用户数据
mysql -u root -p smart_home < 02_insert_users.sql

# 3. 导入操作日志
mysql -u root -p smart_home < 03_insert_device_operations.sql

# 4. 导入环境数据
mysql -u root -p smart_home < 04_insert_environment_data.sql

# 5. 导入习惯分析
mysql -u root -p smart_home < 05_insert_user_habits.sql

# 6. 导入使用统计
mysql -u root -p smart_home < 06_insert_usage_stats.sql

# 7. 导入智能场景
mysql -u root -p smart_home < 07_insert_smart_scenes.sql
```

### 3. 验证数据

```sql
-- 查看用户数量
SELECT COUNT(*) FROM users;

-- 查看操作日志数量
SELECT COUNT(*) FROM device_operations;

-- 查看用户使用习惯
SELECT username, habit_type, confidence_score 
FROM users u 
JOIN user_habits uh ON u.id = uh.user_id;
```

## 🔍 数据挖掘示例查询

### 1. 用户温度偏好分析

```sql
SELECT 
    u.username,
    AVG(JSON_EXTRACT(do.parameters, '$.temperature')) as avg_temperature,
    MIN(JSON_EXTRACT(do.parameters, '$.temperature')) as min_temperature,
    MAX(JSON_EXTRACT(do.parameters, '$.temperature')) as max_temperature,
    COUNT(*) as operation_count
FROM users u
JOIN device_operations do ON u.id = do.user_id
WHERE do.action = 'set_temperature'
GROUP BY u.id, u.username;
```

### 2. 使用时间模式分析

```sql
SELECT 
    u.username,
    HOUR(do.timestamp) as hour,
    COUNT(*) as usage_count
FROM users u
JOIN device_operations do ON u.id = do.user_id
GROUP BY u.id, u.username, HOUR(do.timestamp)
ORDER BY u.username, hour;
```

### 3. 设备使用频率统计

```sql
SELECT 
    device_type,
    COUNT(*) as total_operations,
    AVG(response_time) as avg_response_time
FROM device_operations
GROUP BY device_type;
```

### 4. 用户习惯置信度分析

```sql
SELECT 
    u.username,
    uh.habit_type,
    uh.confidence_score,
    uh.frequency,
    JSON_EXTRACT(uh.pattern_data, '$.preferred_temperature') as preferred_temp
FROM users u
JOIN user_habits uh ON u.id = uh.user_id
WHERE uh.habit_type = 'temperature_preference'
ORDER BY uh.confidence_score DESC;
```

## 📈 数据扩展

### 添加新操作记录

```sql
INSERT INTO device_operations (user_id, device_type, device_name, action, parameters, timestamp) VALUES
(1, 'air_conditioner', '客厅空调', 'set_temperature', '{"temperature": 25}', NOW());
```

### 更新用户习惯

```sql
UPDATE user_habits 
SET pattern_data = JSON_SET(pattern_data, '$.preferred_temperature', 24.5),
    confidence_score = 0.90
WHERE user_id = 1 AND habit_type = 'temperature_preference';
```

## 🔧 数据维护

### 清理历史数据

```sql
-- 删除30天前的操作日志
DELETE FROM device_operations 
WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 删除过期的环境数据
DELETE FROM environment_data 
WHERE timestamp < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

### 数据备份

```bash
# 备份整个数据库
mysqldump -u root -p smart_home > backup_$(date +%Y%m%d).sql

# 备份特定表
mysqldump -u root -p smart_home device_operations user_habits > habits_backup.sql
```

## 📝 注意事项

1. **数据一致性**：确保外键关系正确，避免数据不一致
2. **性能优化**：为经常查询的字段添加索引
3. **数据安全**：定期备份重要数据
4. **隐私保护**：在生产环境中注意用户隐私数据保护
5. **数据更新**：定期更新模拟数据以保持数据新鲜度

---

**提示**：这些数据主要用于开发和测试环境，生产环境请使用真实的用户数据。
