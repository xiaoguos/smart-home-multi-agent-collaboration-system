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
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ========================================
# 环境检查
# ========================================
echo -e "${YELLOW}检查运行环境...${NC}"
echo -e "${YELLOW}Checking runtime environment...${NC}"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ 错误: 未找到Python3${NC}"
    echo -e "${RED}✗ Error: Python3 not found${NC}"
    echo -e "${YELLOW}  请安装 Python 3.8+${NC}"
    exit 1
fi
pythonVersion=$(python3 --version 2>&1)
echo -e "${GREEN}✓ Python: $pythonVersion${NC}"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ 错误: 未找到Node.js${NC}"
    echo -e "${RED}✗ Error: Node.js not found${NC}"
    echo -e "${YELLOW}  请安装 Node.js 16+${NC}"
    exit 1
fi
nodeVersion=$(node --version 2>&1)
echo -e "${GREEN}✓ Node.js: $nodeVersion${NC}"

# 检查 pnpm
if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}✗ 错误: 未找到pnpm${NC}"
    echo -e "${RED}✗ Error: pnpm not found${NC}"
    echo -e "${YELLOW}  请运行: npm install -g pnpm${NC}"
    exit 1
fi
pnpmVersion=$(pnpm --version 2>&1)
echo -e "${GREEN}✓ pnpm: v$pnpmVersion${NC}"

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}✗ 错误: 未找到uv${NC}"
    echo -e "${RED}✗ Error: uv not found${NC}"
    echo -e "${YELLOW}  请运行: pip install uv${NC}"
    echo -e "${YELLOW}  或访问: https://docs.astral.sh/uv/getting-started/installation/${NC}"
    exit 1
fi
uvVersion=$(uv --version 2>&1)
echo -e "${GREEN}✓ uv: $uvVersion${NC}"
echo

# 定位项目根目录
echo -e "${YELLOW}定位项目根目录...${NC}"
echo -e "${YELLOW}Locating project root directory...${NC}"

CURRENT_DIR=$(basename "$PWD")
PARENT_DIR=$(basename "$(dirname "$PWD")")

# 如果在 script/start 目录，向上两级
if [ "$CURRENT_DIR" = "start" ] && [ "$PARENT_DIR" = "script" ]; then
    cd ../..
    echo -e "${GREEN}✓ 已从 script/start 目录切换到项目根目录${NC}"
    echo -e "${GREEN}✓ Switched from script/start directory to project root${NC}"
# 如果在 script 目录，向上一级
elif [ "$CURRENT_DIR" = "script" ]; then
    cd ..
    echo -e "${GREEN}✓ 已从 script 目录切换到项目根目录${NC}"
    echo -e "${GREEN}✓ Switched from script directory to project root${NC}"
fi
echo

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}错误: 未找到配置文件 config.yaml${NC}"
    echo -e "${RED}Error: Configuration file config.yaml not found${NC}"
    echo -e "${RED}当前目录: $PWD${NC}"
    echo -e "${RED}Current directory: $PWD${NC}"
    exit 1
fi

# 读取配置文件中的端口号
echo -e "${YELLOW}读取配置文件...${NC}"
echo -e "${YELLOW}Reading configuration file...${NC}"

# 使用 grep 和 sed 从 YAML 读取端口配置
read_yaml_port() {
    local section=$1
    local key=$2
    grep -A 5 "^${section}:" config.yaml | grep "port:" | head -1 | sed 's/.*port: *\([0-9]*\).*/\1/'
}

# 读取各个服务的端口
backendPort=$(grep -A 10 "^backend:" config.yaml | grep -A 5 "python:" | grep "port:" | sed 's/.*port: *\([0-9]*\).*/\1/')
frontendPort=$(grep -A 5 "^frontend:" config.yaml | grep -A 3 "dev_server:" | grep "port:" | sed 's/.*port: *\([0-9]*\).*/\1/')
conductorPort=$(grep -A 5 "conductor:" config.yaml | grep "port:" | sed 's/.*port: *\([0-9]*\).*/\1/')
airCondPort=$(grep -A 5 "air_conditioner:" config.yaml | grep "port:" | sed 's/.*port: *\([0-9]*\).*/\1/')
airCleanPort=$(grep -A 5 "air_cleaner:" config.yaml | grep "port:" | sed 's/.*port: *\([0-9]*\).*/\1/')
bedsideLampPort=$(grep -A 5 "bedside_lamp:" config.yaml | grep "port:" | sed 's/.*port: *\([0-9]*\).*/\1/')

# 如果读取失败，使用默认值
backendPort=${backendPort:-3000}
frontendPort=${frontendPort:-1420}
conductorPort=${conductorPort:-12000}
airCondPort=${airCondPort:-12001}
airCleanPort=${airCleanPort:-12002}
bedsideLampPort=${bedsideLampPort:-12004}

echo -e "${GREEN}✓ 配置读取完成${NC}"
echo -e "${GREEN}  - 后端端口 / Backend Port: $backendPort${NC}"
echo -e "${GREEN}  - 前端端口 / Frontend Port: $frontendPort${NC}"
echo -e "${GREEN}  - Conductor端口: $conductorPort${NC}"
echo

# 创建必要的目录
mkdir -p logs
mkdir -p temp

# 检查 Python 虚拟环境
echo -e "${YELLOW}检查 Python 虚拟环境...${NC}"
echo -e "${YELLOW}Checking Python virtual environment...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}✗ 虚拟环境不存在，正在创建...${NC}"
    echo -e "${YELLOW}✗ Virtual environment not found, creating...${NC}"
    echo
    
    echo -e "${CYAN}  执行: uv venv${NC}"
    uv venv
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ 虚拟环境创建失败！${NC}"
        echo -e "${RED}✗ Virtual environment creation failed!${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
fi

# 安装 Python 依赖
echo
echo -e "${YELLOW}检查 Python 依赖...${NC}"
echo -e "${YELLOW}Checking Python dependencies...${NC}"

echo -e "${CYAN}  执行: uv pip install -r requirements.txt${NC}"
uv pip install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Python 依赖安装失败！${NC}"
    echo -e "${RED}✗ Python dependency installation failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 依赖安装完成${NC}"

# 检查后端依赖
if [ -f "app/backend-python/requirements.txt" ]; then
    echo -e "${CYAN}  执行: uv pip install -r app/backend-python/requirements.txt${NC}"
    uv pip install -r app/backend-python/requirements.txt --quiet
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ 后端依赖安装失败！${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
fi

# 检查前端依赖
echo
echo -e "${YELLOW}检查前端依赖...${NC}"
echo -e "${YELLOW}Checking frontend dependencies...${NC}"

if [ ! -d "app/node_modules" ]; then
    echo -e "${YELLOW}✗ 前端依赖未安装，正在安装...${NC}"
    echo -e "${YELLOW}✗ Frontend dependencies not installed, installing...${NC}"
    echo
    
    cd app || exit 1
    echo -e "${CYAN}  执行: pnpm install${NC}"
    pnpm install
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ 依赖安装失败！${NC}"
        echo -e "${RED}✗ Dependency installation failed!${NC}"
        exit 1
    fi
    cd - > /dev/null || exit 1
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✓ 前端依赖已安装${NC}"
fi
echo

echo -e "${BLUE}正在启动 Moss AI 本地开发环境...${NC}"
echo -e "${BLUE}Starting Moss AI Local Development Environment...${NC}"
echo

# 函数：检查端口是否监听
check_port() {
    local port=$1
    local max_attempts=5
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if command -v lsof > /dev/null 2>&1; then
            if lsof -i:$port -sTCP:LISTEN > /dev/null 2>&1; then
                return 0
            fi
        elif command -v netstat > /dev/null 2>&1; then
            if netstat -tuln | grep ":$port " > /dev/null 2>&1; then
                return 0
            fi
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    return 1
}

# 函数：启动服务（使用虚拟环境）
start_service() {
    local service_name="$1"
    local service_path="$2"
    local port="$3"
    local step="$4"
    local log_name="$5"
    
    echo -e "${YELLOW}[$step/6] 启动 $service_name (端口 $port)...${NC}"
    echo -e "${YELLOW}[$step/6] Starting $service_name (Port $port)...${NC}"
    
    cd "$service_path" || exit 1
    # 使用虚拟环境中的 python
    nohup ../../.venv/bin/python main.py >> "../../logs/${log_name}.log" 2>&1 &
    local pid=$!
    echo "$pid" > "../../temp/${log_name}.pid"
    cd - > /dev/null || exit 1
    
    echo -e "${CYAN}  等待服务启动...${NC}"
    sleep 3
    
    # 检查端口是否监听
    if ! check_port "$port"; then
        echo -e "${RED}  ✗ $service_name 启动失败！端口 $port 未监听${NC}"
        echo -e "${RED}  ✗ $service_name failed to start! Port $port not listening${NC}"
        echo -e "${YELLOW}  查看日志: logs/${log_name}.log${NC}"
        cleanup
        exit 1
    fi
    
    echo -e "${GREEN}  ✓ $service_name 已启动 (端口 $port 已监听)${NC}"
    echo
}

# 启动Python Agent的函数
start_agent() {
    local agent_name="$1"
    local agent_path="$2"
    local port="$3"
    local step="$4"
    local log_name="$5"
    
    start_service "$agent_name" "$agent_path" "$port" "$step" "$log_name"
}

# ============ 步骤 1: 启动后端服务 ============
start_service "后端服务 / Backend Service" "app/backend-python" "$backendPort" "1" "backend"

# ============ 步骤 2: 启动总管理代理 (Conductor) ============
sleep 1
start_agent "总管理代理 / Conductor Agent" "agents/conductor_agent" "$conductorPort" "2" "conductor_agent"

# ============ 步骤 3-5: 启动子代理 ============
start_agent "空调代理 / Air Conditioner Agent" "agents/air_conditioner_agent" "$airCondPort" "3" "air_conditioner_agent"
start_agent "空气净化器代理 / Air Cleaner Agent" "agents/air_cleaner_agent" "$airCleanPort" "4" "air_cleaner_agent"
start_agent "床头灯代理 / Bedside Lamp Agent" "agents/bedside_lamp_agent" "$bedsideLampPort" "5" "bedside_lamp_agent"

# ============ 步骤 6: 启动前端开发服务器 ============
echo -e "${YELLOW}[6/6] 启动前端开发服务器 (端口 $frontendPort)...${NC}"
echo -e "${YELLOW}[6/6] Starting Frontend Dev Server (Port $frontendPort)...${NC}"
cd app || exit 1
nohup pnpm dev >> "../logs/frontend.log" 2>&1 &
frontend_pid=$!
echo "$frontend_pid" > "../temp/frontend.pid"
cd - > /dev/null || exit 1

echo -e "${CYAN}  等待前端服务启动...${NC}"
sleep 5

# 检查端口是否监听
if ! check_port "$frontendPort"; then
    echo -e "${RED}  ✗ 前端服务启动失败！端口 $frontendPort 未监听${NC}"
    echo -e "${RED}  ✗ Frontend service failed to start! Port $frontendPort not listening${NC}"
    echo -e "${YELLOW}  查看日志: logs/frontend.log${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}  ✓ 前端服务已启动 (端口 $frontendPort 已监听)${NC}"
echo

echo
echo "========================================"
echo -e "${GREEN}所有服务已启动完成！${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo "========================================"
echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    服务地址 / Service URLs                  ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════╣${NC}"
echo
echo -e "${YELLOW}  【前端应用 / Frontend】${NC}"
echo -e "    ${GREEN}http://localhost:$frontendPort${NC}"
echo -e "    ${YELLOW}★ 请在浏览器中打开此地址使用应用 ★${NC}"
echo
echo -e "${BLUE}  【后端服务 / Backend】${NC}"
echo -e "    ${GREEN}http://localhost:$backendPort${NC}"
echo
echo -e "${BLUE}  【智能代理 / Agents】${NC}"
echo -e "    总管理代理 / Conductor:      ${GREEN}http://localhost:$conductorPort${NC}"
echo -e "    空调代理 / Air Conditioner:  ${GREEN}http://localhost:$airCondPort${NC}"
echo -e "    空气净化器 / Air Cleaner:    ${GREEN}http://localhost:$airCleanPort${NC}"
echo -e "    床头灯 / Bedside Lamp:       ${GREEN}http://localhost:$bedsideLampPort${NC}"
echo
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}日志文件位置 / Log Files:${NC}"
echo "  logs/backend.log"
echo "  logs/frontend.log"
echo "  logs/conductor_agent.log"
echo "  logs/air_conditioner_agent.log"
echo "  logs/air_cleaner_agent.log"
echo "  logs/bedside_lamp_agent.log"
echo
# 定义清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止所有服务...${NC}"
    echo -e "${YELLOW}Stopping all services...${NC}"
    echo ""
    
    # 停止所有端口的服务
    for port in $frontendPort $backendPort $conductorPort $airCondPort $airCleanPort $bedsideLampPort; do
        if command -v lsof > /dev/null 2>&1; then
            pid=$(lsof -ti:$port 2>/dev/null)
        else
            pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
        fi
        
        if [ -n "$pid" ]; then
            kill -9 "$pid" 2>/dev/null
            echo -e "${GREEN}✓ 已停止端口 $port 的进程 (PID: $pid)${NC}"
        fi
    done
    
    # 清理 PID 文件
    rm -f temp/*.pid 2>/dev/null
    
    echo ""
    echo -e "${GREEN}所有服务已停止${NC}"
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# 捕获退出信号
trap cleanup EXIT INT TERM

echo ""
echo -e "${RED}关闭此终端将自动停止所有服务${NC}"
echo -e "${RED}Closing this terminal will automatically stop all services${NC}"
echo ""
echo -e "${BLUE}按 Ctrl+C 停止所有服务 / Press Ctrl+C to stop all services${NC}"
echo ""

# 持续运行，监控进程状态
while true; do
    sleep 5
    
    # 检查至少一个服务是否在运行
    running=0
    for port in $frontendPort $backendPort $conductorPort $airCondPort $airCleanPort $bedsideLampPort; do
        if command -v lsof > /dev/null 2>&1; then
            pid=$(lsof -ti:$port 2>/dev/null)
        else
            pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
        fi
        
        if [ -n "$pid" ]; then
            running=1
            break
        fi
    done
    
    if [ $running -eq 0 ]; then
        echo ""
        echo -e "${RED}所有服务进程已意外退出，请检查日志${NC}"
        echo -e "${RED}All service processes have exited unexpectedly${NC}"
        exit 1
    fi
done
