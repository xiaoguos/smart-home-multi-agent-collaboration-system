@echo off
REM Docker部署脚本 (Windows)
REM Docker Deployment Script (Windows)

echo ========================================
echo 智能家居代理系统 Docker部署脚本
echo Smart Home Agent System Docker Deploy
echo ========================================
echo.

REM 设置编码为UTF-8
chcp 65001 >nul

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Docker，请先安装Docker Desktop
    echo Error: Docker not found, please install Docker Desktop first
    pause
    exit /b 1
)

REM 检查Docker Compose是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Docker Compose，请先安装Docker Compose
    echo Error: Docker Compose not found, please install Docker Compose first
    pause
    exit /b 1
)

REM 创建必要的目录
echo 创建必要的目录...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "ssl" mkdir ssl

REM 构建镜像
echo 构建Docker镜像...
docker-compose build

if errorlevel 1 (
    echo 镜像构建失败！
    pause
    exit /b 1
)

REM 启动服务
echo 启动服务...
docker-compose up -d

if errorlevel 1 (
    echo 服务启动失败！
    pause
    exit /b 1
)

REM 等待服务启动
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
docker-compose ps

echo.
echo ========================================
echo 部署完成！
echo Deployment completed!
echo ========================================
echo.
echo 服务地址 / Service URLs:
echo   总管理代理 / Conductor Agent:    http://localhost:12002
echo   空调代理 / Air Conditioner:      http://localhost:12000
echo   空气净化器代理 / Air Cleaner:     http://localhost:12001
echo   数据挖掘代理 / Data Mining:       http://localhost:12003
echo.
echo 通过Nginx访问 / Access via Nginx:
echo   总管理代理: http://conductor.localhost
echo   空调代理: http://ac.localhost
echo   空气净化器代理: http://cleaner.localhost
echo   数据挖掘代理: http://analytics.localhost
echo.
echo 数据库连接 / Database:
echo   StarRocks FE: localhost:9030
echo   StarRocks BE: localhost:9060
echo   Redis: localhost:6379
echo.
echo 查看日志: docker-compose logs -f
echo 停止服务: docker-compose down
echo 重启服务: docker-compose restart
echo.
echo 按任意键关闭此窗口...
pause >nul
