#!/bin/bash
# 智能家居代理系统启动脚本 (Linux/macOS)
# Smart Home Agent System Startup Script (Linux/macOS)

echo "========================================"
echo "智能家居代理系统启动脚本"
echo "Smart Home Agent System Startup Script"
echo "========================================"
echo

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3，请先安装Python 3.8+${NC}"
    echo -e "${RED}Error: Python3 not found, please install Python 3.8+${NC}"
    exit 1
fi

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}错误: 未找到配置文件 config.yaml${NC}"
    echo -e "${RED}Error: Configuration file config.yaml not found${NC}"
    exit 1
fi

# 创建必要的目录
mkdir -p logs
mkdir -p temp

echo -e "${BLUE}正在启动智能家居代理系统...${NC}"
echo -e "${BLUE}Starting Smart Home Agent System...${NC}"
echo

# 函数：启动代理服务
start_agent() {
    local agent_name="$1"
    local agent_path="$2"
    local port="$3"
    local step="$4"
    
    echo -e "${YELLOW}[$step/4] 启动 $agent_name (端口 $port)...${NC}"
    echo -e "${YELLOW}[$step/4] Starting $agent_name (Port $port)...${NC}"
    
    cd "$agent_path" || exit 1
    nohup python3 server.py --host localhost --port "$port" > "../../logs/${agent_name,,}_agent.log" 2>&1 &
    local pid=$!
    echo "$pid" > "../../temp/${agent_name,,}_agent.pid"
    cd - > /dev/null || exit 1
    
    sleep 2
    echo -e "${GREEN}✓ $agent_name 已启动 (PID: $pid)${NC}"
}

# 启动所有代理
start_agent "空调代理" "agents/air_conditioner_agent" "12000" "1"
start_agent "空气净化器代理" "agents/air_cleaner_agent" "12001" "2"
start_agent "数据挖掘代理" "agents/dw_agent" "12003" "3"
start_agent "总管理代理" "agents/conductor_agent" "12002" "4"

echo
echo "========================================"
echo -e "${GREEN}所有代理已启动完成！${NC}"
echo -e "${GREEN}All agents started successfully!${NC}"
echo "========================================"
echo
echo -e "${BLUE}服务地址 / Service URLs:${NC}"
echo "  总管理代理 / Conductor Agent:    http://localhost:12002"
echo "  空调代理 / Air Conditioner:      http://localhost:12000"
echo "  空气净化器代理 / Air Cleaner:     http://localhost:12001"
echo "  数据挖掘代理 / Data Mining:       http://localhost:12003"
echo
echo -e "${BLUE}进程ID文件位置 / PID Files:${NC}"
echo "  temp/conductor_agent.pid"
echo "  temp/air_conditioner_agent.pid"
echo "  temp/air_cleaner_agent.pid"
echo "  temp/data_mining_agent.pid"
echo
echo -e "${BLUE}日志文件位置 / Log Files:${NC}"
echo "  logs/conductor_agent.log"
echo "  logs/air_conditioner_agent.log"
echo "  logs/air_cleaner_agent.log"
echo "  logs/data_mining_agent.log"
echo

# 显示运行状态
echo -e "${YELLOW}检查服务状态...${NC}"
sleep 3

check_service() {
    local port="$1"
    local name="$2"
    
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name (端口 $port) 运行正常${NC}"
    else
        echo -e "${RED}✗ $name (端口 $port) 可能未正常启动${NC}"
    fi
}

check_service "12002" "总管理代理"
check_service "12000" "空调代理"
check_service "12001" "空气净化器代理"
check_service "12003" "数据挖掘代理"

echo
echo -e "${BLUE}使用 'stop_agents.sh' 停止所有服务${NC}"
echo -e "${BLUE}Use 'stop_agents.sh' to stop all services${NC}"
