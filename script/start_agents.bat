@echo off
REM 智能家居代理系统启动脚本 (Windows)
REM Smart Home Agent System Startup Script (Windows)

echo ========================================
echo 智能家居代理系统启动脚本
echo Smart Home Agent System Startup Script
echo ========================================
echo.

REM 设置编码为UTF-8
chcp 65001 >nul

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    echo Error: Python not found, please install Python 3.8+
    pause
    exit /b 1
)

REM 定位项目根目录
echo 定位项目根目录...
echo Locating project root directory...
for %%I in (.) do set CURRENT_DIR=%%~nxI
if "%CURRENT_DIR%"=="script" (
    cd ..
    echo 已从 script 目录切换到项目根目录
    echo Switched from script directory to project root
    echo.
)

REM 检查配置文件
if not exist "config.yaml" (
    echo 错误: 未找到配置文件 config.yaml
    echo Error: Configuration file config.yaml not found
    echo 当前目录: %CD%
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM 创建日志目录
if not exist "logs" mkdir logs

REM 创建临时目录
if not exist "temp" mkdir temp

echo 正在启动智能家居代理系统...
echo Starting Smart Home Agent System...
echo.

REM 启动空调代理
echo [1/5] 启动空调代理 (端口 12001)...
echo [1/5] Starting Air Conditioner Agent (Port 12001)...
start "Air Conditioner Agent" cmd /k "cd /d agents\air_conditioner_agent && python main.py --host localhost --port 12001"
timeout /t 2 /nobreak >nul

REM 启动空气净化器代理
echo [2/5] 启动空气净化器代理 (端口 12002)...
echo [2/5] Starting Air Cleaner Agent (Port 12002)...
start "Air Cleaner Agent" cmd /k "cd /d agents\air_cleaner_agent && python main.py --host localhost --port 12002"
timeout /t 2 /nobreak >nul

REM 启动床头灯代理
echo [3/5] 启动床头灯代理 (端口 12004)...
echo [3/5] Starting Bedside Lamp Agent (Port 12004)...
start "Bedside Lamp Agent" cmd /k "cd /d agents\bedside_lamp_agent && python main.py --host localhost --port 12004"
timeout /t 2 /nobreak >nul

REM 启动数据挖掘代理
echo [4/5] 启动数据挖掘代理 (端口 12003)...
echo [4/5] Starting Data Mining Agent (Port 12003)...
start "Data Mining Agent" cmd /k "cd /d agents\dw_agent && python main.py --host localhost --port 12003"
timeout /t 2 /nobreak >nul

REM 启动总管理代理
echo [5/5] 启动总管理代理 (端口 12000)...
echo [5/5] Starting Conductor Agent (Port 12000)...
start "Conductor Agent" cmd /k "cd /d agents\conductor_agent && python main.py --host localhost --port 12000"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo 所有代理已启动完成！
echo All agents started successfully!
echo ========================================
echo.
echo 服务地址 / Service URLs:
echo   总管理代理 / Conductor Agent:    http://localhost:12000
echo   空调代理 / Air Conditioner:      http://localhost:12001
echo   空气净化器代理 / Air Cleaner:     http://localhost:12002
echo   数据挖掘代理 / Data Mining:       http://localhost:12003
echo   床头灯代理 / Bedside Lamp:        http://localhost:12004
echo.
echo ========================================
echo.
echo 提示：关闭此窗口将自动停止所有服务
echo Note: Closing this window will stop all services
echo.
echo 按任意键停止所有服务并退出...
echo Press any key to stop all services and exit...
pause >nul

echo.
echo 正在停止所有代理服务...
echo Stopping all agent services...
echo.

REM 停止所有监听指定端口的进程
for %%p in (12000 12001 12002 12003 12004) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr "LISTENING" 2^>nul') do (
        echo 停止端口 %%p 的进程 (PID: %%a)
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo.
echo 所有服务已停止
echo All services stopped
timeout /t 2 /nobreak >nul
