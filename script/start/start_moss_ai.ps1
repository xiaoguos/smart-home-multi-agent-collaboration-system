#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# 智能家居代理系统启动脚本 (PowerShell)
# Smart Home Agent System Startup Script (PowerShell)
#
# 架构设计：
#   - 环境检查模块：统一检查所有运行环境
#   - 配置管理模块：集中处理配置文件读取
#   - 服务管理模块：统一启动/停止服务
#   - 工具函数模块：提供可复用的通用功能

# ========================================
# 初始化设置
# ========================================
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

try { chcp 65001 > $null } catch { }

# ========================================
# 全局变量
# ========================================
$script:Config = @{}
$script:Jobs = @()
$script:ProjectRoot = ""

# ========================================
# 工具函数模块
# ========================================
function Write-ColorText {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-ColorText "========================================" "Cyan"
    Write-ColorText $Title "Cyan"
    Write-ColorText "========================================" "Cyan"
    Write-Host ""
}

function Write-Step {
    param(
        [string]$TextCN,
        [string]$TextEN
    )
    Write-ColorText $TextCN "Yellow"
    Write-ColorText $TextEN "Yellow"
    Write-Host ""
}

# ========================================
# 环境检查模块 - 统一检查所有必要的运行环境
# ========================================
function Test-CommandExists {
    param(
        [string]$Command,
        [string]$DisplayName,
        [string]$InstallHint
    )
    
    try {
        $version = & $Command --version 2>&1
        if ($LASTEXITCODE -ne 0) { throw }
        Write-ColorText "✓ $DisplayName`: $version" "Green"
        return $true
    }
    catch {
        Write-ColorText "✗ 错误: 未找到 $DisplayName" "Red"
        Write-ColorText "✗ Error: $DisplayName not found" "Red"
        Write-ColorText "  $InstallHint" "Yellow"
        return $false
    }
}

function Test-Environment {
    Write-Step "检查运行环境..." "Checking runtime environment..."
    
    $checks = @(
        @{ Command = "python"; Name = "Python"; Hint = "请安装 Python 3.8+ / Please install Python 3.8+" },
        @{ Command = "node"; Name = "Node.js"; Hint = "请安装 Node.js 16+ / Please install Node.js 16+" },
        @{ Command = "pnpm"; Name = "pnpm"; Hint = "请运行: npm install -g pnpm" },
        @{ Command = "uv"; Name = "uv"; Hint = "请运行: pip install uv 或访问 https://docs.astral.sh/uv/" }
    )
    
    $allPassed = $true
    foreach ($check in $checks) {
        if (-not (Test-CommandExists -Command $check.Command -DisplayName $check.Name -InstallHint $check.Hint)) {
            $allPassed = $false
        }
    }
    
    if (-not $allPassed) {
        Read-Host "按Enter键退出 / Press Enter to exit"
        exit 1
    }
}

# ========================================
# 项目定位模块 - 自动定位项目根目录
# ========================================
function Find-ProjectRoot {
    Write-Step "定位项目根目录..." "Locating project root directory..."
    
    $paths = @(".", "..", "..\..")
    
    foreach ($path in $paths) {
        $configPath = Join-Path $path "config.yaml"
        if (Test-Path $configPath) {
            Set-Location $path
            $script:ProjectRoot = (Get-Location).Path
            Write-ColorText "✓ 配置文件已找到: $script:ProjectRoot" "Green"
            Write-ColorText "✓ Configuration file found: $script:ProjectRoot" "Green"
            return $true
        }
    }
    
    Write-ColorText "✗ 错误: 未找到配置文件 config.yaml" "Red"
    Write-ColorText "✗ Error: Configuration file config.yaml not found" "Red"
    Write-ColorText "   当前目录: $PWD" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

# ========================================
# 配置管理模块 - 集中处理配置读取和默认值
# ========================================
function Read-YamlConfig {
    param([string]$Pattern, [int]$DefaultValue)
    
    $yamlContent = Get-Content "config.yaml" -Raw
    if ($yamlContent -match $Pattern) {
        return [int]$matches[1]
    }
    return $DefaultValue
}

function Initialize-Config {
    Write-Step "读取配置文件..." "Reading configuration file..."
    
    # 定义配置映射：Pattern, Key, DefaultValue
    $configMappings = @(
        @{ Pattern = "backend:[\s\S]*?python:[\s\S]*?port:\s*(\d+)"; Key = "BackendPort"; Default = 3000 },
        @{ Pattern = "frontend:[\s\S]*?dev_server:[\s\S]*?port:\s*(\d+)"; Key = "FrontendPort"; Default = 1420 },
        @{ Pattern = "conductor:[\s\S]*?port:\s*(\d+)"; Key = "ConductorPort"; Default = 12000 },
        @{ Pattern = "air_conditioner:[\s\S]*?port:\s*(\d+)"; Key = "AirCondPort"; Default = 12001 },
        @{ Pattern = "air_cleaner:[\s\S]*?port:\s*(\d+)"; Key = "AirCleanPort"; Default = 12002 },
        @{ Pattern = "bedside_lamp:[\s\S]*?port:\s*(\d+)"; Key = "BedsideLampPort"; Default = 12004 }
    )
    
    foreach ($mapping in $configMappings) {
        $script:Config[$mapping.Key] = Read-YamlConfig -Pattern $mapping.Pattern -DefaultValue $mapping.Default
    }
    
    Write-ColorText "✓ 配置读取完成" "Green"
    Write-ColorText "  - 后端端口 / Backend Port: $($script:Config.BackendPort)" "Gray"
    Write-ColorText "  - 前端端口 / Frontend Port: $($script:Config.FrontendPort)" "Gray"
    Write-ColorText "  - Conductor端口: $($script:Config.ConductorPort)" "Gray"
}

# ========================================
# 目录准备模块 - 创建必要的目录
# ========================================
function Initialize-Directories {
    Write-Step "创建必要的目录..." "Creating necessary directories..."
    
    $directories = @("logs", "temp")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
            Write-ColorText "✓ 创建目录: $dir" "Green"
        }
    }
}

# ========================================
# 环境准备模块 - Python虚拟环境和依赖
# ========================================
function Initialize-PythonEnvironment {
    Write-Step "检查 Python 虚拟环境..." "Checking Python virtual environment..."
    
    if (-not (Test-Path ".venv")) {
        Write-ColorText "✗ 虚拟环境不存在，正在创建..." "Yellow"
        Write-ColorText "  执行: uv venv" "Gray"
        & uv venv
        
        if ($LASTEXITCODE -ne 0) {
            Write-ColorText "✗ 虚拟环境创建失败！" "Red"
            throw "Virtual environment creation failed"
        }
        Write-ColorText "✓ 虚拟环境创建完成" "Green"
    }
    else {
        Write-ColorText "✓ 虚拟环境已存在" "Green"
    }
    
    Write-Host ""
    Write-Step "安装 Python 依赖..." "Installing Python dependencies..."
    Write-ColorText "  执行: uv sync" "Gray"
    & uv sync
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "✗ Python 依赖安装失败！" "Red"
        throw "Python dependencies installation failed"
    }
    Write-ColorText "✓ Python 依赖已安装" "Green"
}

function Initialize-FrontendDependencies {
    Write-Step "检查前端依赖..." "Checking frontend dependencies..."
    
    if (-not (Test-Path "app\node_modules")) {
        Write-ColorText "✗ 前端依赖未安装，正在安装..." "Yellow"
        Write-Host ""
        
        Push-Location "app"
        Write-ColorText "  执行: pnpm install" "Gray"
        & pnpm install
        
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-ColorText "✗ 依赖安装失败！" "Red"
            throw "Frontend dependencies installation failed"
        }
        Pop-Location
        Write-ColorText "✓ 依赖安装完成" "Green"
    }
    else {
        Write-ColorText "✓ 前端依赖已安装" "Green"
    }
}

# ========================================
# 服务启动模块 - 统一管理所有服务启动
# ========================================
function Start-ServiceProcess {
    param(
        [int]$Index,
        [string]$NameCN,
        [string]$NameEN,
        [string]$Directory,
        [string]$Command,
        [int]$Port,
        [int]$Delay
    )
    
    Write-ColorText "[$Index/6] 启动$NameCN (端口 $Port)..." "Cyan"
    Write-ColorText "[$Index/6] Starting $NameEN (Port $Port)..." "Cyan"
    
    $fullPath = Join-Path $script:ProjectRoot $Directory
    
    $job = Start-Job -ScriptBlock {
        param($Path, $Cmd)
        Set-Location $Path
        Invoke-Expression $Cmd
    } -ArgumentList $fullPath, $Command -Name $NameEN
    
    $script:Jobs += @{
        Job = $job
        Name = $NameEN
        Port = $Port
    }
    
    Start-Sleep -Seconds $Delay
    Write-ColorText "  ✓ $NameCN`已启动" "Green"
    Write-ColorText "  ✓ $NameEN started" "Green"
    Write-Host ""
}

function Start-AllServices {
    Write-Section "正在启动 Moss AI 本地开发环境...`nStarting Moss AI Local Development Environment..."
    
    # 定义服务配置：Index, NameCN, NameEN, Directory, Command, PortKey, Delay
    $services = @(
        @{Index=1; NameCN="后端服务"; NameEN="Backend Service"; Dir="app\backend-python"; Cmd="python __main__.py"; PortKey="BackendPort"; Delay=3},
        @{Index=2; NameCN="总管理代理"; NameEN="Conductor Agent"; Dir="agents\conductor_agent"; Cmd="python __main__.py"; PortKey="ConductorPort"; Delay=3},
        @{Index=3; NameCN="空调代理"; NameEN="Air Conditioner Agent"; Dir="agents\air_conditioner_agent"; Cmd="python __main__.py"; PortKey="AirCondPort"; Delay=2},
        @{Index=4; NameCN="空气净化器代理"; NameEN="Air Cleaner Agent"; Dir="agents\air_cleaner_agent"; Cmd="python __main__.py"; PortKey="AirCleanPort"; Delay=2},
        @{Index=5; NameCN="床头灯代理"; NameEN="Bedside Lamp Agent"; Dir="agents\bedside_lamp_agent"; Cmd="python __main__.py"; PortKey="BedsideLampPort"; Delay=2},
        @{Index=6; NameCN="前端开发服务器"; NameEN="Frontend Dev Server"; Dir="app"; Cmd="pnpm dev"; PortKey="FrontendPort"; Delay=3}
    )
    
    foreach ($service in $services) {
        Start-ServiceProcess -Index $service.Index -NameCN $service.NameCN -NameEN $service.NameEN `
            -Directory $service.Dir -Command $service.Cmd -Port $script:Config[$service.PortKey] -Delay $service.Delay
    }
}

# ========================================
# 信息显示模块 - 显示服务地址和使用说明
# ========================================
function Show-ServiceInfo {
    Write-Section "所有服务已启动完成！`nAll services started successfully!"
    
    Write-ColorText "╔════════════════════════════════════════════════════════════╗" "Cyan"
    Write-ColorText "║                    服务地址 / Service URLs                  ║" "Cyan"
    Write-ColorText "╠════════════════════════════════════════════════════════════╣" "Cyan"
    Write-ColorText "║                                                            ║" "Cyan"
    Write-ColorText "║  【前端应用 / Frontend】                                     ║" "Cyan"
    Write-ColorText "║    http://localhost:$($script:Config.FrontendPort)" "Yellow"
    Write-ColorText "║    ★ 请在浏览器中打开此地址使用应用                           ║" "Cyan"
    Write-ColorText "║                                                            ║" "Cyan"
    Write-ColorText "║  【后端服务 / Backend】                                      ║" "Cyan"
    Write-ColorText "║    http://localhost:$($script:Config.BackendPort)" "White"
    Write-ColorText "║                                                            ║" "Cyan"
    Write-ColorText "║  【智能代理 / Agents】                                       ║" "Cyan"
    Write-ColorText "║    总管理代理 / Conductor:      http://localhost:$($script:Config.ConductorPort)" "White"
    Write-ColorText "║    空调代理 / Air Conditioner:  http://localhost:$($script:Config.AirCondPort)" "White"
    Write-ColorText "║    空气净化器 / Air Cleaner:    http://localhost:$($script:Config.AirCleanPort)" "White"
    Write-ColorText "║    床头灯 / Bedside Lamp:       http://localhost:$($script:Config.BedsideLampPort)" "White"
    Write-ColorText "║                                                            ║" "Cyan"
    Write-ColorText "╚════════════════════════════════════════════════════════════╝" "Cyan"
    Write-Host ""
}

# ========================================
# 服务停止模块 - 统一停止所有服务
# ========================================
function Stop-AllServices {
    Write-Host ""
    Write-ColorText "正在停止所有服务..." "Yellow"
    Write-ColorText "Stopping all services..." "Yellow"
    Write-Host ""
    
    # 停止所有后台任务
    foreach ($jobInfo in $script:Jobs) {
        if ($jobInfo.Job.State -eq 'Running') {
            Write-ColorText "停止服务: $($jobInfo.Name)" "Gray"
            Stop-Job -Job $jobInfo.Job
            Remove-Job -Job $jobInfo.Job -Force
        }
    }
    
    # 停止端口占用的进程
    $ports = @(
        $script:Config.FrontendPort, 
        $script:Config.BackendPort, 
        $script:Config.ConductorPort,
        $script:Config.AirCondPort,
        $script:Config.AirCleanPort,
        $script:Config.BedsideLampPort
    )
    
    foreach ($port in $ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Write-ColorText "停止端口 $port 的进程: $($process.Name) (PID: $($process.Id))" "Gray"
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    
    Write-ColorText "✓ 所有服务已停止" "Green"
    Write-ColorText "✓ All services stopped" "Green"
}

# ========================================
# 主流程
# ========================================
function Main {
    try {
        Clear-Host
        Write-Section "智能家居代理系统启动脚本`nSmart Home Agent System Startup Script"
        
        Test-Environment
        Find-ProjectRoot
        Initialize-Config
        Initialize-Directories
        Initialize-PythonEnvironment
        Initialize-FrontendDependencies
        Start-AllServices
        Show-ServiceInfo
        
        Write-ColorText "提示：按 Ctrl+C 停止所有服务并退出" "Yellow"
        Write-ColorText "Note: Press Ctrl+C to stop all services and exit" "Yellow"
        Write-Host ""
        
        # 等待用户中断
        try {
            while ($true) {
                Start-Sleep -Seconds 1
            }
        }
        catch {
            # Ctrl+C 被按下
        }
    }
    catch {
        Write-ColorText "`n✗ 发生错误: $_" "Red"
        Write-ColorText "✗ Error occurred: $_" "Red"
    }
    finally {
        Stop-AllServices
        Start-Sleep -Seconds 2
    }
}

# 运行主程序
Main
