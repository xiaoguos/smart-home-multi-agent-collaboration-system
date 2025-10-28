#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# 智能家居代理系统启动脚本 (PowerShell)
# Smart Home Agent System Startup Script (PowerShell)

# 强制设置UTF-8编码
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# 静默设置代码页为UTF-8
try { chcp 65001 > $null } catch { }

function Write-ColorText {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

Clear-Host

Write-ColorText "========================================" "Cyan"
Write-ColorText "智能家居代理系统启动脚本" "Cyan"
Write-ColorText "Smart Home Agent System Startup Script" "Cyan"
Write-ColorText "========================================" "Cyan"
Write-Host ""

# ========================================
# 环境检查
# ========================================
Write-ColorText "检查运行环境..." "Yellow"
Write-ColorText "Checking runtime environment..." "Yellow"
Write-Host ""

# 检查 Python
try {
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-ColorText "✓ Python: $pythonVersion" "Green"
} catch {
    Write-ColorText "✗ 错误: 未找到Python" "Red"
    Write-ColorText "✗ Error: Python not found" "Red"
    Write-ColorText "  请安装 Python 3.8+ / Please install Python 3.8+" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

# 检查 Node.js
try {
    $nodeVersion = & node --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Node.js not found"
    }
    Write-ColorText "✓ Node.js: $nodeVersion" "Green"
} catch {
    Write-ColorText "✗ 错误: 未找到Node.js" "Red"
    Write-ColorText "✗ Error: Node.js not found" "Red"
    Write-ColorText "  请安装 Node.js 16+ / Please install Node.js 16+" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

# 检查 pnpm
try {
    $pnpmVersion = & pnpm --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pnpm not found"
    }
    Write-ColorText "✓ pnpm: v$pnpmVersion" "Green"
} catch {
    Write-ColorText "✗ 错误: 未找到pnpm" "Red"
    Write-ColorText "✗ Error: pnpm not found" "Red"
    Write-ColorText "  请运行: npm install -g pnpm" "Yellow"
    Write-ColorText "  Please run: npm install -g pnpm" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

# 检查 uv
try {
    $uvVersion = & uv --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "uv not found"
    }
    Write-ColorText "✓ uv: $uvVersion" "Green"
} catch {
    Write-ColorText "✗ 错误: 未找到uv" "Red"
    Write-ColorText "✗ Error: uv not found" "Red"
    Write-ColorText "  请运行: pip install uv" "Yellow"
    Write-ColorText "  Please run: pip install uv" "Yellow"
    Write-ColorText "  或访问: https://docs.astral.sh/uv/getting-started/installation/" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

# 定位项目根目录
Write-Host ""
Write-ColorText "定位项目根目录..." "Yellow"
Write-ColorText "Locating project root directory..." "Yellow"

# 确定配置文件路径并切换到项目根目录
$configPath = $null
if (Test-Path "config.yaml") {
    $configPath = "config.yaml"
    Write-ColorText "✓ 已在项目根目录" "Green"
} elseif (Test-Path "..\config.yaml") {
    Set-Location ..
    $configPath = "config.yaml"
    Write-ColorText "✓ 已从 script 目录切换到项目根目录" "Green"
} elseif (Test-Path "..\..\config.yaml") {
    Set-Location ..\..
    $configPath = "config.yaml"
    Write-ColorText "✓ 已从 script/start 目录切换到项目根目录" "Green"
} else {
    Write-ColorText "✗ 错误: 未找到配置文件 config.yaml" "Red"
    Write-ColorText "✗ Error: Configuration file config.yaml not found" "Red"
    Write-ColorText "   当前目录: $PWD" "Yellow"
    Write-ColorText "   Current directory: $PWD" "Yellow"
    Write-ColorText "   请确保在项目根目录、script目录或script/start目录下运行此脚本" "Yellow"
    Write-ColorText "   Please run this script from project root, script, or script/start directory" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

Write-ColorText "✓ 配置文件存在: $configPath" "Green"
Write-ColorText "✓ Configuration file exists: $configPath" "Green"

# 解析 YAML 配置文件
Write-Host ""
Write-ColorText "读取配置文件..." "Yellow"
Write-ColorText "Reading configuration file..." "Yellow"

function Get-YamlValue {
    param(
        [string]$FilePath,
        [string]$Key
    )
    $content = Get-Content $FilePath -Raw
    if ($content -match "$Key\s*:\s*(\S+)") {
        return $matches[1].Trim('"').Trim("'")
    }
    return $null
}

# 读取配置
$config = @{
    Backend = @{
        Host = (Get-YamlValue "config.yaml" "host") -replace "0.0.0.0", "localhost"
        Port = [int](Get-YamlValue "config.yaml" "port")
    }
    Frontend = @{
        Port = 1420  # 从 frontend.dev_server.port 读取
    }
    Agents = @{
        Conductor = @{
            Port = 12000
            Name = "总管理代理 / Conductor Agent"
        }
        AirConditioner = @{
            Port = 12001
            Name = "空调代理 / Air Conditioner Agent"
        }
        AirCleaner = @{
            Port = 12002
            Name = "空气净化器代理 / Air Cleaner Agent"
        }
        BedsideLamp = @{
            Port = 12004
            Name = "床头灯代理 / Bedside Lamp Agent"
        }
    }
}

# 从 YAML 中读取更详细的配置
$yamlContent = Get-Content "config.yaml" -Raw

# 读取前端端口
if ($yamlContent -match "frontend:[\s\S]*?port:\s*(\d+)") {
    $config.Frontend.Port = [int]$matches[1]
}

# 读取 Agent 端口
if ($yamlContent -match "conductor:[\s\S]*?port:\s*(\d+)") {
    $config.Agents.Conductor.Port = [int]$matches[1]
}
if ($yamlContent -match "air_conditioner:[\s\S]*?port:\s*(\d+)") {
    $config.Agents.AirConditioner.Port = [int]$matches[1]
}
if ($yamlContent -match "air_cleaner:[\s\S]*?port:\s*(\d+)") {
    $config.Agents.AirCleaner.Port = [int]$matches[1]
}
if ($yamlContent -match "bedside_lamp:[\s\S]*?port:\s*(\d+)") {
    $config.Agents.BedsideLamp.Port = [int]$matches[1]
}

Write-ColorText "✓ 配置读取完成" "Green"
Write-ColorText "  - 后端端口 / Backend Port: $($config.Backend.Port)" "Gray"
Write-ColorText "  - 前端端口 / Frontend Port: $($config.Frontend.Port)" "Gray"
Write-ColorText "  - Conductor端口: $($config.Agents.Conductor.Port)" "Gray"

# 创建必要的目录
Write-Host ""
Write-ColorText "创建必要的目录..." "Yellow"
Write-ColorText "Creating necessary directories..." "Yellow"

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-ColorText "✓ 创建日志目录" "Green"
}

if (-not (Test-Path "temp")) {
    New-Item -ItemType Directory -Path "temp" | Out-Null
    Write-ColorText "✓ 创建临时目录" "Green"
}

Write-Host ""
Write-ColorText "检查 Python 虚拟环境..." "Yellow"
Write-ColorText "Checking Python virtual environment..." "Yellow"

# 检查 .venv 是否存在
if (-not (Test-Path ".venv")) {
    Write-ColorText "✗ 虚拟环境不存在，正在创建..." "Yellow"
    Write-ColorText "✗ Virtual environment not found, creating..." "Yellow"
    Write-Host ""
    
    Write-ColorText "  执行: uv venv" "Gray"
    & uv venv
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "✗ 虚拟环境创建失败！" "Red"
        Write-ColorText "✗ Virtual environment creation failed!" "Red"
        Read-Host "按Enter键退出 / Press Enter to exit"
        exit 1
    }
    Write-ColorText "✓ 虚拟环境创建完成" "Green"
} else {
    Write-ColorText "✓ 虚拟环境已存在" "Green"
}

# 安装 Python 依赖
Write-Host ""
Write-ColorText "检查 Python 依赖..." "Yellow"
Write-ColorText "Checking Python dependencies..." "Yellow"

Write-ColorText "  执行: uv pip install -r requirements.txt" "Gray"
& uv pip install -r requirements.txt --quiet

if ($LASTEXITCODE -ne 0) {
    Write-ColorText "✗ Python 依赖安装失败！" "Red"
    Write-ColorText "✗ Python dependency installation failed!" "Red"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}
Write-ColorText "✓ Python 依赖安装完成" "Green"

# 检查后端依赖
if (Test-Path "app\backend-python\requirements.txt") {
    Write-ColorText "  执行: uv pip install -r app/backend-python/requirements.txt" "Gray"
    & uv pip install -r app\backend-python\requirements.txt --quiet
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "✗ 后端依赖安装失败！" "Red"
        Read-Host "按Enter键退出 / Press Enter to exit"
        exit 1
    }
    Write-ColorText "✓ 后端依赖安装完成" "Green"
}

Write-Host ""
Write-ColorText "检查前端依赖..." "Yellow"
Write-ColorText "Checking frontend dependencies..." "Yellow"

# 检查 node_modules 是否存在
if (-not (Test-Path "app\node_modules")) {
    Write-ColorText "✗ 前端依赖未安装，正在安装..." "Yellow"
    Write-ColorText "✗ Frontend dependencies not installed, installing..." "Yellow"
    Write-Host ""
    
    Push-Location app
    Write-ColorText "  执行: pnpm install" "Gray"
    & pnpm install
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "✗ 依赖安装失败！" "Red"
        Write-ColorText "✗ Dependency installation failed!" "Red"
        Pop-Location
        Read-Host "按Enter键退出 / Press Enter to exit"
        exit 1
    }
    Pop-Location
    Write-ColorText "✓ 依赖安装完成" "Green"
} else {
    Write-ColorText "✓ 前端依赖已安装" "Green"
}

Write-Host ""
Write-ColorText "正在启动 Moss AI 本地开发环境..." "Cyan"
Write-ColorText "Starting Moss AI Local Development Environment..." "Cyan"
Write-Host ""

# 存储所有进程信息
$processes = @()

# 错误处理函数
function Stop-AllProcesses {
    Write-Host ""
    Write-ColorText "检测到错误，正在停止所有已启动的服务..." "Red"
    Write-ColorText "Error detected, stopping all started services..." "Red"
    
    foreach ($proc in $global:processes) {
        try {
            if ($proc.Process -and !$proc.Process.HasExited) {
                Stop-Process -Id $proc.Process.Id -Force -ErrorAction SilentlyContinue
                Write-ColorText "  ✓ 已停止 $($proc.Name)" "Yellow"
            }
        } catch { }
    }
    
    Write-ColorText "脚本已终止" "Red"
    Write-ColorText "Script terminated" "Red"
    exit 1
}

$global:processes = @()

# ============ 步骤 1: 启动后端服务 ============
$backendPort = $config.Backend.Port
Write-ColorText "[1/6] 启动后端服务 (端口 $backendPort)..." "Yellow"
Write-ColorText "[1/6] Starting Backend Service (Port $backendPort)..." "Yellow"

$logPath = "$PWD\logs\backend.log"
# 使用 uv run 在虚拟环境中运行
$process = Start-Process cmd -ArgumentList "/c `"cd /d $PWD\app\backend-python && $PWD\.venv\Scripts\python.exe main.py > $logPath 2>&1`"" `
    -WindowStyle Hidden `
    -PassThru

$processes += @{Name="后端服务 / Backend Service"; Port=$backendPort; Process=$process; LogPath=$logPath; Type="Backend"}
$global:processes = $processes

# 等待服务启动并检查端口
Write-ColorText "  等待服务启动..." "Gray"
Start-Sleep -Seconds 3

# 检查端口是否监听
$portListening = $false
for ($i = 0; $i -lt 5; $i++) {
    $conn = Test-NetConnection -ComputerName localhost -Port $backendPort -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($conn) {
        $portListening = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $portListening) {
    Write-ColorText "  ✗ 后端服务启动失败！端口 $backendPort 未监听" "Red"
    Write-ColorText "  ✗ Backend service failed to start! Port $backendPort not listening" "Red"
    Write-ColorText "  查看日志: $logPath" "Yellow"
    Stop-AllProcesses
}
Write-ColorText "  ✓ 后端服务已启动 (端口 $backendPort 已监听)" "Green"
Write-Host ""

# ============ 步骤 2: 启动总管理代理 (Conductor) ============
$conductorPort = $config.Agents.Conductor.Port
Write-ColorText "[2/6] 启动总管理代理 (端口 $conductorPort)..." "Yellow"
Write-ColorText "[2/6] Starting Conductor Agent (Port $conductorPort)..." "Yellow"

$logPath = "$PWD\logs\conductor_agent.log"
$process = Start-Process cmd -ArgumentList "/c `"cd /d $PWD\agents\conductor_agent && $PWD\.venv\Scripts\python.exe main.py > $logPath 2>&1`"" `
    -WindowStyle Hidden `
    -PassThru

$processes += @{Name="总管理代理 / Conductor Agent"; Port=$conductorPort; Process=$process; LogPath=$logPath; Type="Agent"}
$global:processes = $processes

Write-ColorText "  等待服务启动..." "Gray"
Start-Sleep -Seconds 3

$portListening = $false
for ($i = 0; $i -lt 5; $i++) {
    $conn = Test-NetConnection -ComputerName localhost -Port $conductorPort -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($conn) {
        $portListening = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $portListening) {
    Write-ColorText "  ✗ Conductor启动失败！端口 $conductorPort 未监听" "Red"
    Write-ColorText "  查看日志: $logPath" "Yellow"
    Stop-AllProcesses
}
Write-ColorText "  ✓ 总管理代理已启动 (端口 $conductorPort 已监听)" "Green"
Write-Host ""

# ============ 步骤 3-5: 启动子代理 ============
$agentList = @(
    @{ Folder="air_conditioner_agent"; NameCN="空调代理"; NameEN="Air Conditioner Agent"; Port=$config.Agents.AirConditioner.Port; Step=3 },
    @{ Folder="air_cleaner_agent"; NameCN="空气净化器代理"; NameEN="Air Cleaner Agent"; Port=$config.Agents.AirCleaner.Port; Step=4 },
    @{ Folder="bedside_lamp_agent"; NameCN="床头灯代理"; NameEN="Bedside Lamp Agent"; Port=$config.Agents.BedsideLamp.Port; Step=5 }
)

foreach ($agent in $agentList) {
    Write-ColorText "[$($agent.Step)/6] 启动$($agent.NameCN) (端口 $($agent.Port))..." "Yellow"
    Write-ColorText "[$($agent.Step)/6] Starting $($agent.NameEN) (Port $($agent.Port))..." "Yellow"
    
    $logPath = "$PWD\logs\$($agent.Folder).log"
    $process = Start-Process cmd -ArgumentList "/c `"cd /d $PWD\agents\$($agent.Folder) && $PWD\.venv\Scripts\python.exe main.py > $logPath 2>&1`"" `
        -WindowStyle Hidden `
        -PassThru
    
    $processes += @{Name="$($agent.NameCN) / $($agent.NameEN)"; Port=$agent.Port; Process=$process; LogPath=$logPath; Type="Agent"}
    $global:processes = $processes
    
    Write-ColorText "  等待服务启动..." "Gray"
    Start-Sleep -Seconds 3
    
    $portListening = $false
    for ($i = 0; $i -lt 5; $i++) {
        $conn = Test-NetConnection -ComputerName localhost -Port $agent.Port -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($conn) {
            $portListening = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    
    if (-not $portListening) {
        Write-ColorText "  ✗ $($agent.NameCN) 启动失败！端口 $($agent.Port) 未监听" "Red"
        Write-ColorText "  查看日志: $logPath" "Yellow"
        Stop-AllProcesses
    }
    Write-ColorText "  ✓ 已启动 (端口 $($agent.Port) 已监听)" "Green"
    Write-Host ""
}

# ============ 步骤 6: 启动前端开发服务器 ============
$frontendPort = $config.Frontend.Port
Write-ColorText "[6/6] 启动前端开发服务器 (端口 $frontendPort)..." "Yellow"
Write-ColorText "[6/6] Starting Frontend Dev Server (Port $frontendPort)..." "Yellow"

# 使用 cmd 来启动 pnpm，避免 PowerShell 执行策略问题
$process = Start-Process cmd -ArgumentList "/c `"cd /d $PWD\app && pnpm dev`"" `
    -WindowStyle Minimized `
    -PassThru

$logPath = "$PWD\logs\frontend.log"
$processes += @{Name="前端服务 / Frontend Dev Server"; Port=$frontendPort; Process=$process; LogPath=$logPath; Type="Frontend"}
$global:processes = $processes

Write-ColorText "  等待前端服务启动..." "Gray"
Start-Sleep -Seconds 5

$portListening = $false
for ($i = 0; $i -lt 10; $i++) {
    $conn = Test-NetConnection -ComputerName localhost -Port $frontendPort -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($conn) {
        $portListening = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $portListening) {
    Write-ColorText "  ✗ 前端服务启动失败！端口 $frontendPort 未监听" "Red"
    Write-ColorText "  ✗ Frontend service failed to start! Port $frontendPort not listening" "Red"
    Write-ColorText "  提示: 请检查前端窗口查看详细错误" "Yellow"
    Stop-AllProcesses
}
Write-ColorText "  ✓ 前端服务已启动 (端口 $frontendPort 已监听)" "Green"
Write-ColorText "  提示: 前端窗口已最小化" "Gray"

Write-Host ""
Write-ColorText "========================================" "Green"
Write-ColorText "所有服务已启动完成！" "Green"
Write-ColorText "All services started successfully!" "Green"
Write-ColorText "========================================" "Green"
Write-Host ""

# 显示服务地址
Write-ColorText "╔════════════════════════════════════════════════════════════╗" "Cyan"
Write-ColorText "║                    服务地址 / Service URLs                  ║" "Cyan"
Write-ColorText "╠════════════════════════════════════════════════════════════╣" "Cyan"
Write-Host ""

# 前端服务 - 重点显示
Write-ColorText "  【前端应用 / Frontend】" "Magenta"
Write-Host "    " -NoNewline
Write-ColorText "http://localhost:$($config.Frontend.Port)" "Green"
Write-ColorText "    ★ 请在浏览器中打开此地址使用应用 ★" "Yellow"
Write-Host ""

# 后端服务
Write-ColorText "  【后端服务 / Backend】" "Cyan"
Write-Host "    " -NoNewline
Write-ColorText "http://localhost:$($config.Backend.Port)" "Green"
Write-Host ""

# 智能代理
Write-ColorText "  【智能代理 / Agents】" "Cyan"
$agentProcs = $processes | Where-Object { $_.Type -eq "Agent" }
foreach ($proc in $agentProcs) {
    $name = $proc.Name.Split('/')[0].Trim()
    Write-Host "    $name" -NoNewline -ForegroundColor White
    Write-Host ": " -NoNewline
    Write-ColorText "http://localhost:$($proc.Port)" "Green"
}
Write-Host ""

Write-ColorText "╚════════════════════════════════════════════════════════════╝" "Cyan"
Write-Host ""

# 详细进程信息
Write-ColorText "进程详情 / Process Details:" "Yellow"
Write-Host ""
foreach ($proc in $processes) {
    Write-ColorText "  [$($proc.Name)]" "White"
    Write-Host "    进程 ID / PID:  " -NoNewline -ForegroundColor Gray
    Write-ColorText "$($proc.Process.Id)" "Cyan"
    Write-Host "    日志路径 / Log: " -NoNewline -ForegroundColor Gray
    Write-ColorText "$($proc.LogPath)" "Gray"
}

Write-ColorText "========================================" "Cyan"
Write-Host ""
Write-ColorText "使用说明 / Instructions:" "Yellow"
Write-ColorText "  • 所有服务已在后台运行" "White"
Write-ColorText "    All services are running in the background" "Gray"
Write-ColorText "  • 日志输出到 logs/ 目录" "White"
Write-ColorText "    Logs are saved to logs/ directory" "Gray"
Write-ColorText "  • 关闭此窗口将自动停止所有服务" "Red"
Write-ColorText "    Closing this window will automatically stop all services" "Red"
Write-Host ""

# 注册退出事件处理
$cleanupScript = {
    Write-Host ""
    Write-ColorText "正在停止所有代理服务..." "Yellow"
    Write-ColorText "Stopping all agent services..." "Yellow"
    
    foreach ($proc in $global:agentProcesses) {
        try {
            if ($proc.Process -and !$proc.Process.HasExited) {
                Stop-Process -Id $proc.Process.Id -Force -ErrorAction SilentlyContinue
                Write-ColorText "  ✓ 已停止 $($proc.Name)" "Green"
            }
        } catch { }
    }
    
    Write-ColorText "所有服务已停止" "Green"
    Write-ColorText "All services stopped" "Green"
}

# 将进程信息存储到全局变量
$global:agentProcesses = $processes

# 注册控制台关闭事件
try {
    $null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanupScript
} catch { }

Write-ColorText "按 Ctrl+C 或关闭此窗口来停止所有服务" "Cyan"
Write-ColorText "Press Ctrl+C or close this window to stop all services" "Cyan"
Write-Host ""

# 持续运行，等待用户中断
try {
    while ($true) {
        Start-Sleep -Seconds 5
        
        # 检查进程是否还在运行
        $runningCount = 0
        foreach ($proc in $processes) {
            if ($proc.Process -and !$proc.Process.HasExited) {
                $runningCount++
            }
        }
        
        if ($runningCount -eq 0) {
            Write-ColorText "所有代理进程已意外退出，请检查日志" "Red"
            Write-ColorText "All agent processes have exited unexpectedly, please check logs" "Red"
            break
        }
    }
} catch {
    # Ctrl+C 被按下
} finally {
    # 清理所有进程
    Write-Host ""
    Write-ColorText "正在停止所有代理服务..." "Yellow"
    Write-ColorText "Stopping all agent services..." "Yellow"
    
    foreach ($proc in $processes) {
        try {
            if ($proc.Process -and !$proc.Process.HasExited) {
                Stop-Process -Id $proc.Process.Id -Force -ErrorAction SilentlyContinue
                Write-ColorText "  ✓ 已停止 $($proc.Name)" "Green"
            }
        } catch { }
    }
    
    Write-ColorText "所有服务已停止" "Green"
    Write-ColorText "All services stopped" "Green"
    Start-Sleep -Seconds 2
}

