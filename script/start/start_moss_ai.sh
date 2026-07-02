#!/bin/bash
# 智能家居代理系统启动脚本 (Linux/macOS)
# Smart Home Agent System Startup Script (Linux/macOS)
#
# 架构设计：
#   - 环境检查模块：统一检查所有运行环境
#   - 配置管理模块：集中处理配置文件读取
#   - 服务管理模块：统一启动/停止服务
#   - 工具函数模块：提供可复用的通用功能

# ========================================
# 初始化设置
# ========================================
set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

# 全局变量
declare -A CONFIG
declare -a PIDS
PROJECT_ROOT=""

# ========================================
# 工具函数模块
# ========================================
print_section() {
    echo
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}$2${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${GRAY}  $1${NC}"
}

# ========================================
# 环境检查模块 - 统一检查所有必要的运行环境
# ========================================
check_command() {
    local cmd=$1
    local name=$2
    local hint=$3
    
    if ! command -v "$cmd" &> /dev/null; then
        print_error "错误: 未找到 $name"
        print_error "Error: $name not found"
        echo -e "${YELLOW}  $hint${NC}"
        return 1
    fi
    
    local version=$("$cmd" --version 2>&1 | head -1)
    print_success "$name: $version"
    return 0
}

check_environment() {
    print_step "检查运行环境..." "Checking runtime environment..."
    
    local all_passed=1
    
    check_command "python3" "Python" "请安装 Python 3.8+ / Please install Python 3.8+" || all_passed=0
    check_command "node" "Node.js" "请安装 Node.js 16+ / Please install Node.js 16+" || all_passed=0
    check_command "pnpm" "pnpm" "请运行: npm install -g pnpm" || all_passed=0
    check_command "uv" "uv" "请运行: pip install uv 或访问 https://docs.astral.sh/uv/" || all_passed=0
    
    echo
    
    if [ $all_passed -eq 0 ]; then
        exit 1
    fi
}

# ========================================
# 项目定位模块 - 自动定位项目根目录
# ========================================
find_project_root() {
    print_step "定位项目根目录..." "Locating project root directory..."
    
    local paths=("." ".." "../..")
    
    for path in "${paths[@]}"; do
        if [ -f "$path/config.yaml" ]; then
            cd "$path" || exit 1
            PROJECT_ROOT=$(pwd)
            print_success "配置文件已找到: $PROJECT_ROOT"
            print_success "Configuration file found: $PROJECT_ROOT"
            return 0
        fi
    done
    
    print_error "错误: 未找到配置文件 config.yaml"
    print_error "Error: Configuration file config.yaml not found"
    print_error "当前目录: $PWD"
    exit 1
}

# ========================================
# 配置管理模块 - 集中处理配置读取和默认值
# ========================================
read_yaml_port() {
    local pattern=$1
    local default=$2
    
    local port=$(grep -E "$pattern" config.yaml | head -1 | sed 's/.*port: *\([0-9]*\).*/\1/')
    echo "${port:-$default}"
}

initialize_config() {
    print_step "读取配置文件..." "Reading configuration file..."
    
    # 定义配置映射：pattern|key|default
    local configs=(
        "backend:.*python:.*port:|BackendPort|3000"
        "frontend:.*dev_server:.*port:|FrontendPort|1420"
        "conductor:.*port:|ConductorPort|12000"
        "air_conditioner:.*port:|AirCondPort|12001"
        "air_cleaner:.*port:|AirCleanPort|12002"
        "bedside_lamp:.*port:|BedsideLampPort|12004"
    )
    
    for config_line in "${configs[@]}"; do
        IFS='|' read -r pattern key default <<< "$config_line"
        CONFIG[$key]=$(read_yaml_port "$pattern" "$default")
    done
    
    print_success "配置读取完成"
    print_info "后端端口 / Backend Port: ${CONFIG[BackendPort]}"
    print_info "前端端口 / Frontend Port: ${CONFIG[FrontendPort]}"
    print_info "Conductor端口: ${CONFIG[ConductorPort]}"
    echo
}

# ========================================
# 目录准备模块 - 创建必要的目录
# ========================================
initialize_directories() {
    mkdir -p logs temp
}

# ========================================
# 环境准备模块 - Python虚拟环境和依赖
# ========================================
initialize_python_environment() {
    print_step "检查 Python 虚拟环境..." "Checking Python virtual environment..."
    
    if [ ! -d ".venv" ]; then
        print_error "虚拟环境不存在，正在创建..."
        print_error "Virtual environment not found, creating..."
        print_info "执行: uv venv"
        uv venv
        
        if [ $? -ne 0 ]; then
            print_error "虚拟环境创建失败！"
            print_error "Virtual environment creation failed!"
            exit 1
        fi
        print_success "虚拟环境创建完成"
    else
        print_success "虚拟环境已存在"
    fi
    
    echo
    print_step "安装 Python 依赖..." "Installing Python dependencies..."
    print_info "执行: uv sync"
    uv sync
    
    if [ $? -ne 0 ]; then
        print_error "Python 依赖安装失败！"
        print_error "Python dependencies installation failed!"
        exit 1
    fi
    print_success "Python 依赖已安装"
}

initialize_frontend_dependencies() {
    print_step "检查前端依赖..." "Checking frontend dependencies..."
    
    if [ ! -d "app/node_modules" ]; then
        print_error "前端依赖未安装，正在安装..."
        print_error "Frontend dependencies not installed, installing..."
        echo
        
        cd app || exit 1
        print_info "执行: pnpm install"
        pnpm install
        
        if [ $? -ne 0 ]; then
            cd ..
            print_error "依赖安装失败！"
            print_error "Dependency installation failed!"
            exit 1
        fi
        cd ..
        print_success "依赖安装完成"
    else
        print_success "前端依赖已安装"
    fi
    echo
}

# ========================================
# 服务启动模块 - 统一管理所有服务启动
# ========================================
start_service() {
    local index=$1
    local name_cn=$2
    local name_en=$3
    local directory=$4
    local command=$5
    local port_key=$6
    local delay=$7
    
    local port=${CONFIG[$port_key]}
    
    echo -e "${CYAN}[$index/6] 启动$name_cn (端口 $port)...${NC}"
    echo -e "${CYAN}[$index/6] Starting $name_en (Port $port)...${NC}"
    
    cd "$PROJECT_ROOT/$directory" || exit 1
    
    # 启动服务并重定向输出到日志
    eval "$command" >> "$PROJECT_ROOT/logs/${name_en// /_}.log" 2>&1 &
    local pid=$!
    PIDS+=($pid)
    
    cd "$PROJECT_ROOT" || exit 1
    sleep "$delay"
    
    print_success "$name_cn 已启动"
    print_success "$name_en started"
    echo
}

start_all_services() {
    print_section "正在启动 Smart Home Multi-Agent Collaboration System 本地开发环境...
Starting Smart Home Multi-Agent Collaboration System Local Development Environment..."
    
    # 定义服务配置：index|name_cn|name_en|directory|command|port_key|delay
    local services=(
        "1|后端服务|Backend Service|app/backend-python|uv run .|BackendPort|3"
        "2|总管理代理|Conductor Agent|agents/conductor_agent|uv run .|ConductorPort|3"
        "3|空调代理|Air Conditioner Agent|agents/air_conditioner_agent|uv run .|AirCondPort|2"
        "4|空气净化器|Air Cleaner Agent|agents/air_cleaner_agent|uv run .|AirCleanPort|2"
        "5|床头灯代理|Bedside Lamp Agent|agents/bedside_lamp_agent|uv run .|BedsideLampPort|2"
        "6|前端开发服务器|Frontend Dev Server|app|pnpm dev|FrontendPort|3"
    )
    
    for service_config in "${services[@]}"; do
        IFS='|' read -r idx name_cn name_en dir cmd port_key delay <<< "$service_config"
        start_service "$idx" "$name_cn" "$name_en" "$dir" "$cmd" "$port_key" "$delay"
    done
    
    print_info "所有服务窗口正在后台运行"
    print_info "All services are running in background"
    echo
}

# ========================================
# 信息显示模块 - 显示服务地址和使用说明
# ========================================
show_service_info() {
    print_section "所有服务已启动完成！
All services started successfully!"
    
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    服务地址 / Service URLs                  ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║  【前端应用 / Frontend】                                     ║${NC}"
    echo -e "${YELLOW}║    http://localhost:${CONFIG[FrontendPort]}${NC}"
    echo -e "${CYAN}║    ★ 请在浏览器中打开此地址使用应用                           ║${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║  【后端服务 / Backend】                                      ║${NC}"
    echo -e "${NC}║    http://localhost:${CONFIG[BackendPort]}${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║  【智能代理 / Agents】                                       ║${NC}"
    echo -e "${NC}║    总管理代理 / Conductor:      http://localhost:${CONFIG[ConductorPort]}${NC}"
    echo -e "${NC}║    空调代理 / Air Conditioner:  http://localhost:${CONFIG[AirCondPort]}${NC}"
    echo -e "${NC}║    空气净化器 / Air Cleaner:    http://localhost:${CONFIG[AirCleanPort]}${NC}"
    echo -e "${NC}║    床头灯 / Bedside Lamp:       http://localhost:${CONFIG[BedsideLampPort]}${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# ========================================
# 服务停止模块 - 统一停止所有服务
# ========================================
stop_all_services() {
    echo
    print_step "正在停止所有服务..." "Stopping all services..."
    
    # 停止所有启动的进程
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            print_info "停止进程 PID: $pid"
            kill "$pid" 2>/dev/null || true
        fi
    done
    
    # 停止端口占用的进程
    local ports=(
        "${CONFIG[FrontendPort]}" 
        "${CONFIG[BackendPort]}" 
        "${CONFIG[ConductorPort]}"
        "${CONFIG[AirCondPort]}"
        "${CONFIG[AirCleanPort]}"
        "${CONFIG[BedsideLampPort]}"
    )
    
    for port in "${ports[@]}"; do
        # Linux
        if command -v lsof &> /dev/null; then
            local pid=$(lsof -ti:"$port" 2>/dev/null || true)
            if [ -n "$pid" ]; then
                print_info "停止端口 $port 的进程 (PID: $pid)"
                kill "$pid" 2>/dev/null || true
            fi
        # macOS alternative
        elif command -v netstat &> /dev/null; then
            local pid=$(netstat -vanp tcp 2>/dev/null | grep "\.$port " | awk '{print $9}' | head -1)
            if [ -n "$pid" ]; then
                print_info "停止端口 $port 的进程 (PID: $pid)"
                kill "$pid" 2>/dev/null || true
            fi
        fi
    done
    
    print_success "所有服务已停止"
    print_success "All services stopped"
}

# ========================================
# 信号处理 - 捕获 Ctrl+C 等中断信号
# ========================================
cleanup() {
    stop_all_services
    exit 0
}

trap cleanup SIGINT SIGTERM

# ========================================
# 主流程
# ========================================
main() {
    clear
    print_section "智能家居代理系统启动脚本
Smart Home Agent System Startup Script"
    
    check_environment
    find_project_root
    initialize_config
    initialize_directories
    initialize_python_environment
    initialize_frontend_dependencies
    start_all_services
    show_service_info
    
    echo -e "${YELLOW}提示：按 Ctrl+C 停止所有服务并退出${NC}"
    echo -e "${YELLOW}Note: Press Ctrl+C to stop all services and exit${NC}"
    echo
    
    # 等待用户中断
    wait
}

# 运行主程序
main
