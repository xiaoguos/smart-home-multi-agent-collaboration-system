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

# 检查Python是否安装
Write-ColorText "检查Python环境..." "Yellow"
Write-ColorText "Checking Python environment..." "Yellow"

try {
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-ColorText "✓ Python已安装: $pythonVersion" "Green"
    Write-ColorText "✓ Python installed: $pythonVersion" "Green"
} catch {
    Write-ColorText "✗ 错误: 未找到Python，请先安装Python 3.8+" "Red"
    Write-ColorText "✗ Error: Python not found, please install Python 3.8+" "Red"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}

# 检查配置文件
Write-Host ""
Write-ColorText "检查配置文件..." "Yellow"
Write-ColorText "Checking configuration file..." "Yellow"

# 确定配置文件路径
$configPath = if (Test-Path "config.yaml") {
    "config.yaml"
} elseif (Test-Path "..\config.yaml") {
    "..\config.yaml"
} else {
    $null
}

if (-not $configPath) {
    Write-ColorText "✗ 错误: 未找到配置文件 config.yaml" "Red"
    Write-ColorText "✗ Error: Configuration file config.yaml not found" "Red"
    Write-ColorText "   请确保在项目根目录或script目录下运行此脚本" "Yellow"
    Write-ColorText "   Please run this script from project root or script directory" "Yellow"
    Read-Host "按Enter键退出 / Press Enter to exit"
    exit 1
}
Write-ColorText "✓ 配置文件存在" "Green"
Write-ColorText "✓ Configuration file exists" "Green"

# 切换到项目根目录
if (Test-Path "..\config.yaml") {
    Set-Location ..
    Write-ColorText "✓ 已切换到项目根目录" "Green"
}

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
Write-ColorText "正在启动智能家居代理系统..." "Cyan"
Write-ColorText "Starting Smart Home Agent System..." "Cyan"
Write-Host ""

# 存储所有进程信息
$processes = @()

# 启动空调代理
Write-ColorText "[1/5] 启动空调代理 (端口 12001)..." "Yellow"
Write-ColorText "[1/5] Starting Air Conditioner Agent (Port 12001)..." "Yellow"
$acLogPath = "$PWD\logs\air_conditioner_agent.log"
$acProcess = Start-Process python -ArgumentList "main.py", "--host", "localhost", "--port", "12001" `
    -WorkingDirectory "$PWD\agents\air_conditioner_agent" `
    -WindowStyle Hidden `
    -PassThru
$processes += @{Name="空调代理 / Air Conditioner Agent"; Port=12001; Process=$acProcess; LogPath=$acLogPath}
Write-ColorText "  ✓ 已启动 (PID: $($acProcess.Id))" "Green"
Start-Sleep -Seconds 2

# 启动空气净化器代理
Write-ColorText "[2/5] 启动空气净化器代理 (端口 12002)..." "Yellow"
Write-ColorText "[2/5] Starting Air Cleaner Agent (Port 12002)..." "Yellow"
$cleanerLogPath = "$PWD\logs\air_cleaner_agent.log"
$cleanerProcess = Start-Process python -ArgumentList "main.py", "--host", "localhost", "--port", "12002" `
    -WorkingDirectory "$PWD\agents\air_cleaner_agent" `
    -WindowStyle Hidden `
    -PassThru
$processes += @{Name="空气净化器代理 / Air Cleaner Agent"; Port=12002; Process=$cleanerProcess; LogPath=$cleanerLogPath}
Write-ColorText "  ✓ 已启动 (PID: $($cleanerProcess.Id))" "Green"
Start-Sleep -Seconds 2

# 启动床头灯代理
Write-ColorText "[3/5] 启动床头灯代理 (端口 12004)..." "Yellow"
Write-ColorText "[3/5] Starting Bedside Lamp Agent (Port 12004)..." "Yellow"
$lampLogPath = "$PWD\logs\bedside_lamp_agent.log"
$lampProcess = Start-Process python -ArgumentList "main.py", "--host", "localhost", "--port", "12004" `
    -WorkingDirectory "$PWD\agents\bedside_lamp_agent" `
    -WindowStyle Hidden `
    -PassThru
$processes += @{Name="床头灯代理 / Bedside Lamp Agent"; Port=12004; Process=$lampProcess; LogPath=$lampLogPath}
Write-ColorText "  ✓ 已启动 (PID: $($lampProcess.Id))" "Green"
Start-Sleep -Seconds 2

# 启动数据挖掘代理
Write-ColorText "[4/5] 启动数据挖掘代理 (端口 12003)..." "Yellow"
Write-ColorText "[4/5] Starting Data Mining Agent (Port 12003)..." "Yellow"
$dwLogPath = "$PWD\logs\dw_agent.log"
$dwProcess = Start-Process python -ArgumentList "main.py", "--host", "localhost", "--port", "12003" `
    -WorkingDirectory "$PWD\agents\dw_agent" `
    -WindowStyle Hidden `
    -PassThru
$processes += @{Name="数据挖掘代理 / Data Mining Agent"; Port=12003; Process=$dwProcess; LogPath=$dwLogPath}
Write-ColorText "  ✓ 已启动 (PID: $($dwProcess.Id))" "Green"
Start-Sleep -Seconds 2

# 启动总管理代理
Write-ColorText "[5/5] 启动总管理代理 (端口 12000)..." "Yellow"
Write-ColorText "[5/5] Starting Conductor Agent (Port 12000)..." "Yellow"
$conductorLogPath = "$PWD\logs\conductor_agent.log"
$conductorProcess = Start-Process python -ArgumentList "main.py", "--host", "localhost", "--port", "12000" `
    -WorkingDirectory "$PWD\agents\conductor_agent" `
    -WindowStyle Hidden `
    -PassThru
$processes += @{Name="总管理代理 / Conductor Agent"; Port=12000; Process=$conductorProcess; LogPath=$conductorLogPath}
Write-ColorText "  ✓ 已启动 (PID: $($conductorProcess.Id))" "Green"
Start-Sleep -Seconds 2

Write-Host ""
Write-ColorText "========================================" "Green"
Write-ColorText "所有代理已启动完成！" "Green"
Write-ColorText "All agents started successfully!" "Green"
Write-ColorText "========================================" "Green"
Write-Host ""

# 显示服务汇总信息
Write-ColorText "服务汇总 / Service Summary:" "Cyan"
Write-Host ""
foreach ($proc in $processes) {
    Write-ColorText "[$($proc.Name)]" "White"
    Write-Host "  服务地址 / URL:    " -NoNewline -ForegroundColor Gray
    Write-ColorText "http://localhost:$($proc.Port)" "Green"
    Write-Host "  进程 ID / PID:     " -NoNewline -ForegroundColor Gray
    Write-ColorText "$($proc.Process.Id)" "Cyan"
    Write-Host "  日志路径 / Log:    " -NoNewline -ForegroundColor Gray
    Write-ColorText "$($proc.LogPath)" "Yellow"
    Write-Host ""
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

