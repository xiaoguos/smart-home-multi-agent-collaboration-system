#!/bin/bash
# Docker部署脚本
# Docker Deployment Script

echo "========================================"
echo "智能家居代理系统 Docker部署脚本"
echo "Smart Home Agent System Docker Deploy"
echo "========================================"
echo

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未找到Docker，请先安装Docker${NC}"
    echo -e "${RED}Error: Docker not found, please install Docker first${NC}"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: 未找到Docker Compose，请先安装Docker Compose${NC}"
    echo -e "${RED}Error: Docker Compose not found, please install Docker Compose first${NC}"
    exit 1
fi

# 创建必要的目录
echo -e "${BLUE}创建必要的目录...${NC}"
mkdir -p logs data ssl

# 构建镜像
echo -e "${BLUE}构建Docker镜像...${NC}"
docker-compose build

if [ $? -ne 0 ]; then
    echo -e "${RED}镜像构建失败！${NC}"
    exit 1
fi

# 启动服务
echo -e "${BLUE}启动服务...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}服务启动失败！${NC}"
    exit 1
fi

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 10

# 检查服务状态
echo -e "${BLUE}检查服务状态...${NC}"
docker-compose ps

echo
echo "========================================"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}Deployment completed!${NC}"
echo "========================================"
echo
echo -e "${BLUE}服务地址 / Service URLs:${NC}"
echo "  总管理代理 / Conductor Agent:    http://localhost:12002"
echo "  空调代理 / Air Conditioner:      http://localhost:12000"
echo "  空气净化器代理 / Air Cleaner:     http://localhost:12001"
echo "  数据挖掘代理 / Data Mining:       http://localhost:12003"
echo
echo -e "${BLUE}通过Nginx访问 / Access via Nginx:${NC}"
echo "  总管理代理: http://conductor.localhost"
echo "  空调代理: http://ac.localhost"
echo "  空气净化器代理: http://cleaner.localhost"
echo "  数据挖掘代理: http://analytics.localhost"
echo
echo -e "${BLUE}数据库连接 / Database:${NC}"
echo "  StarRocks FE: localhost:9030"
echo "  StarRocks BE: localhost:9060"
echo "  Redis: localhost:6379"
echo
echo -e "${YELLOW}查看日志: docker-compose logs -f${NC}"
echo -e "${YELLOW}停止服务: docker-compose down${NC}"
echo -e "${YELLOW}重启服务: docker-compose restart${NC}"
