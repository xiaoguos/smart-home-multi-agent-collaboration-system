# Docker 部署指南

## 概述

本文档介绍如何使用Docker部署智能家居代理系统。系统包含多个代理服务，支持StarRocks数据库，并提供完整的容器化解决方案。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Nginx     │  │   Redis     │  │ StarRocks   │         │
│  │ (Reverse    │  │  (Cache)    │  │ (Database)  │         │
│  │  Proxy)     │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          │                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Smart Home Agents Container               ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      ││
│  │  │ Conductor   │ │ Air Cond.   │ │ Air Cleaner │      ││
│  │  │ Agent       │ │ Agent       │ │ Agent       │      ││
│  │  │ :12002      │ │ :12000      │ │ :12001      │      ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘      ││
│  │  ┌─────────────┐                                      ││
│  │  │ Data Mining │                                      ││
│  │  │ Agent       │                                      ││
│  │  │ :12003      │                                      ││
│  │  └─────────────┘                                      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 2. 克隆项目

```bash
git clone <your-repo-url>
cd moss-ai
```

### 3. 配置数据库

编辑 `config.yaml` 文件，配置StarRocks连接信息：

```yaml
database:
  type: "starrocks"
  starrocks:
    host: "starrocks-fe"  # Docker服务名
    port: 9030
    user: "root"
    password: "password"
    database: "smart_home"
```

### 4. 启动服务

#### Linux/macOS
```bash
chmod +x docker-deploy.sh
./docker-deploy.sh
```

#### Windows
```cmd
docker-deploy.bat
```

#### 手动启动
```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

## 服务访问

### 直接访问代理服务

- **总管理代理**: http://localhost:12002
- **空调代理**: http://localhost:12000
- **空气净化器代理**: http://localhost:12001
- **数据挖掘代理**: http://localhost:12003

### 通过Nginx反向代理访问

- **总管理代理**: http://conductor.localhost
- **空调代理**: http://ac.localhost
- **空气净化器代理**: http://cleaner.localhost
- **数据挖掘代理**: http://analytics.localhost

### 数据库访问

- **StarRocks FE**: http://localhost:9030
- **StarRocks BE**: http://localhost:9060
- **Redis**: localhost:6379

## 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f smart-home-agents
```

### 容器管理

```bash
# 进入容器
docker-compose exec smart-home-agents bash

# 查看容器资源使用
docker stats

# 清理未使用的镜像和容器
docker system prune -a
```

### 数据库管理

```bash
# 连接StarRocks
docker-compose exec starrocks-fe mysql -h localhost -P 9030 -u root

# 连接Redis
docker-compose exec redis redis-cli
```

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| PYTHONPATH | /app | Python路径 |
| TZ | Asia/Shanghai | 时区设置 |

### 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| 总管理代理 | 12002 | 12002 | 主要API接口 |
| 空调代理 | 12000 | 12000 | 空调控制 |
| 空气净化器代理 | 12001 | 12001 | 空气净化器控制 |
| 数据挖掘代理 | 12003 | 12003 | 数据分析 |
| StarRocks FE | 9030 | 9030 | 数据库前端 |
| StarRocks BE | 9060 | 9060 | 数据库后端 |
| Redis | 6379 | 6379 | 缓存服务 |
| Nginx | 80 | 80 | Web服务器 |

### 数据卷

| 卷名 | 挂载点 | 说明 |
|------|--------|------|
| starrocks-fe-data | /opt/starrocks/fe/meta | StarRocks FE元数据 |
| starrocks-be-data | /opt/starrocks/be/storage | StarRocks BE数据 |
| redis-data | /data | Redis数据 |
| ./logs | /app/logs | 应用日志 |
| ./data | /app/data | 应用数据 |

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :12002
   
   # 修改docker-compose.yml中的端口映射
   ports:
     - "12003:12002"  # 将主机端口改为12003
   ```

2. **内存不足**
   ```bash
   # 检查内存使用
   docker stats
   
   # 增加Docker内存限制
   # 在Docker Desktop设置中调整资源限制
   ```

3. **数据库连接失败**
   ```bash
   # 检查StarRocks状态
   docker-compose logs starrocks-fe
   docker-compose logs starrocks-be
   
   # 重启数据库服务
   docker-compose restart starrocks-fe starrocks-be
   ```

4. **代理服务启动失败**
   ```bash
   # 查看详细日志
   docker-compose logs smart-home-agents
   
   # 检查配置文件
   docker-compose exec smart-home-agents cat /app/config.yaml
   ```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs smart-home-agents

# 实时查看日志
docker-compose logs -f

# 查看最近100行日志
docker-compose logs --tail=100
```

### 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看系统资源
docker system df

# 查看网络连接
docker network ls
docker network inspect moss-ai_smart-home-network
```

## 生产环境部署

### 安全配置

1. **修改默认密码**
   ```yaml
   # config.yaml
   database:
     starrocks:
       password: "your-secure-password"
   ```

2. **启用HTTPS**
   ```bash
   # 将SSL证书放入ssl目录
   cp your-cert.pem ssl/
   cp your-key.pem ssl/
   
   # 修改nginx.conf启用HTTPS
   ```

3. **限制网络访问**
   ```yaml
   # docker-compose.yml
   services:
     smart-home-agents:
       networks:
         - smart-home-network
       # 不暴露端口到主机
       # ports: []  # 注释掉端口映射
   ```

### 备份和恢复

```bash
# 备份数据库
docker-compose exec starrocks-fe mysqldump -u root -p smart_home > backup.sql

# 备份应用数据
tar -czf app-data-backup.tar.gz data/ logs/

# 恢复数据库
docker-compose exec -T starrocks-fe mysql -u root -p smart_home < backup.sql
```

### 扩展部署

```bash
# 水平扩展代理服务
docker-compose up -d --scale smart-home-agents=3

# 使用负载均衡器
# 配置nginx.conf添加upstream配置
```

## 开发环境

### 开发模式启动

```bash
# 挂载源代码进行开发
docker-compose -f docker-compose.dev.yml up -d
```

### 调试模式

```bash
# 进入容器调试
docker-compose exec smart-home-agents bash

# 查看Python进程
ps aux | grep python

# 查看网络连接
netstat -tulpn
```

## 更新和维护

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build --no-cache

# 重启服务
docker-compose up -d
```

### 清理资源

```bash
# 清理未使用的镜像
docker image prune

# 清理未使用的容器
docker container prune

# 清理未使用的网络
docker network prune

# 清理所有未使用的资源
docker system prune -a
```

---

**注意**: 在生产环境中部署前，请确保：
1. 修改所有默认密码
2. 配置适当的防火墙规则
3. 设置定期备份策略
4. 监控系统资源使用情况
