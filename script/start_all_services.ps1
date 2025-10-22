# Moss AI - 启动所有服务
# 该脚本会依次启动所有必要的服务

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   Moss AI 服务启动脚本" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 环境
Write-Host "[1/2] 检查 Python 环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python 已安装: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查依赖是否安装
Write-Host ""
Write-Host "[2/2] 检查 Python 依赖..." -ForegroundColor Yellow
$a2aInstalled = python -c "import a2a" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ A2A SDK 已安装" -ForegroundColor Green
} else {
    Write-Host "! A2A SDK 未安装，正在安装依赖..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "✗ 依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "正在启动服务..." -ForegroundColor Yellow
Write-Host ""

# 启动 Conductor Agent (A2A Server)
Write-Host "正在启动 Conductor Agent (端口: 12000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd agents\conductor_agent; Write-Host 'Conductor Agent (A2A Server)' -ForegroundColor Green; python main.py --host localhost --port 12000"
Start-Sleep -Seconds 3

# 启动 Cangjie 后端服务
Write-Host "正在启动 Cangjie 后端服务 (端口: 2100)..." -ForegroundColor Cyan
if (Test-Path "app\backend\dist\release\bin\main.exe") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd app\backend; Write-Host 'Cangjie Backend Server' -ForegroundColor Green; .\dist\release\bin\main.exe"
    Start-Sleep -Seconds 2
} elseif (Test-Path "app\backend\dist\debug\bin\main.exe") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd app\backend; Write-Host 'Cangjie Backend Server (Debug)' -ForegroundColor Green; .\dist\debug\bin\main.exe"
    Start-Sleep -Seconds 2
} else {
    Write-Host "✗ 后端可执行文件不存在，请先运行: cd app\backend && cjpm build" -ForegroundColor Red
    Write-Host "提示：请手动编译后端后再次运行此脚本" -ForegroundColor Yellow
}

# 启动前端开发服务器
Write-Host "正在启动前端开发服务器..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd app; Write-Host 'Frontend Dev Server' -ForegroundColor Green; pnpm dev"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   所有服务已启动！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "服务地址:" -ForegroundColor Yellow
Write-Host "  - Conductor Agent (A2A): http://localhost:12000" -ForegroundColor White
Write-Host "  - Cangjie 后端:         http://127.0.0.1:2100" -ForegroundColor White
Write-Host "  - 前端开发服务器:        http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "测试连接:" -ForegroundColor Yellow
Write-Host "  curl http://localhost:12000/" -ForegroundColor Gray
Write-Host "  curl http://127.0.0.1:2100/hello" -ForegroundColor Gray
Write-Host ""
Write-Host "按 Ctrl+C 停止此脚本（服务将继续在独立窗口中运行）" -ForegroundColor Gray
Write-Host ""

# 等待用户输入
Read-Host "按 Enter 键关闭此窗口"

