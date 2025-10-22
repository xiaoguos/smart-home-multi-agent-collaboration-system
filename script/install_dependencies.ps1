# 安装所有项目依赖
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   Moss AI 依赖安装脚本" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python
Write-Host "[1/3] 检查 Python 环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ 未找到 Python" -ForegroundColor Red
    Write-Host "  请访问 https://www.python.org/ 下载安装 Python 3.8+" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 2. 安装 Python 依赖
Write-Host "[2/3] 安装 Python 依赖..." -ForegroundColor Yellow
Write-Host "  正在安装: flask, flask-cors, langchain, etc..." -ForegroundColor Gray
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "✗ Python 依赖安装失败" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 3. 安装前端依赖
Write-Host "[3/3] 安装前端依赖..." -ForegroundColor Yellow

# 检查 pnpm
$pnpmExists = Get-Command pnpm -ErrorAction SilentlyContinue
if ($pnpmExists) {
    Write-Host "  使用 pnpm 安装..." -ForegroundColor Gray
    cd app
    pnpm install
    cd ..
} else {
    # 检查 npm
    $npmExists = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmExists) {
        Write-Host "  使用 npm 安装..." -ForegroundColor Gray
        cd app
        npm install
        cd ..
    } else {
        Write-Host "✗ 未找到 npm 或 pnpm" -ForegroundColor Red
        Write-Host "  请先安装 Node.js: https://nodejs.org/" -ForegroundColor Yellow
        exit 1
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 前端依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "✗ 前端依赖安装失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   所有依赖安装完成！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 编译 Cangjie 后端: cd app\backend && cjpm build" -ForegroundColor White
Write-Host "  2. 运行启动脚本: .\script\start_all_services.ps1" -ForegroundColor White
Write-Host ""

Read-Host "按 Enter 键退出"

