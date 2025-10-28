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

REM ========================================
REM 环境检查
REM ========================================
echo 检查运行环境...
echo Checking runtime environment...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: 未找到Python
    echo ✗ Error: Python not found
    echo   请安装 Python 3.8+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set pythonVer=%%i
echo ✓ Python: %pythonVer%

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: 未找到Node.js
    echo ✗ Error: Node.js not found
    echo   请安装 Node.js 16+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set nodeVer=%%i
echo ✓ Node.js: %nodeVer%

REM 检查 pnpm
pnpm --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: 未找到pnpm
    echo ✗ Error: pnpm not found
    echo   请运行: npm install -g pnpm
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('pnpm --version') do set pnpmVer=%%i
echo ✓ pnpm: v%pnpmVer%
echo.

REM 定位项目根目录
echo 定位项目根目录...
echo Locating project root directory...

REM 检查并切换到项目根目录
if exist "config.yaml" (
    echo ✓ 已在项目根目录
    echo ✓ Already in project root
    goto :found_config
)

if exist "..\config.yaml" (
    cd ..
    echo ✓ 已从 script 目录切换到项目根目录
    echo ✓ Switched from script directory to project root
    goto :found_config
)

if exist "..\..\config.yaml" (
    cd ..\..
    echo ✓ 已从 script/start 目录切换到项目根目录
    echo ✓ Switched from script/start directory to project root
    goto :found_config
)

REM 未找到配置文件
echo 错误: 未找到配置文件 config.yaml
echo Error: Configuration file config.yaml not found
echo 当前目录: %CD%
echo Current directory: %CD%
echo 请确保在项目根目录、script目录或script/start目录下运行此脚本
echo Please run this script from project root, script, or script/start directory
pause
exit /b 1

:found_config
echo ✓ 配置文件已找到
echo ✓ Configuration file found
echo.

REM 读取配置文件中的端口
echo 读取配置文件...
echo Reading configuration file...

REM 使用 Python 读取 YAML 配置（更可靠的方式）
python -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['backend']['python']['port'])" > temp_backend_port.txt 2>nul
python -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['frontend']['dev_server']['port'])" > temp_frontend_port.txt 2>nul
python -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['agents']['conductor']['port'])" > temp_conductor_port.txt 2>nul
python -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['agents']['air_conditioner']['port'])" > temp_aircond_port.txt 2>nul
python -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['agents']['air_cleaner']['port'])" > temp_airclean_port.txt 2>nul
python -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['agents']['bedside_lamp']['port'])" > temp_lamp_port.txt 2>nul

REM 读取文件内容到变量
set /p backendPort=<temp_backend_port.txt
set /p frontendPort=<temp_frontend_port.txt
set /p conductorPort=<temp_conductor_port.txt
set /p airCondPort=<temp_aircond_port.txt
set /p airCleanPort=<temp_airclean_port.txt
set /p bedsideLampPort=<temp_lamp_port.txt

REM 清理临时文件
del temp_*.txt 2>nul

REM 设置默认值（如果读取失败）
if not defined backendPort set backendPort=3000
if not defined frontendPort set frontendPort=1420
if not defined conductorPort set conductorPort=12000
if not defined airCondPort set airCondPort=12001
if not defined airCleanPort set airCleanPort=12002
if not defined bedsideLampPort set bedsideLampPort=12004

echo ✓ 配置读取完成
echo   - 后端端口 / Backend Port: %backendPort%
echo   - 前端端口 / Frontend Port: %frontendPort%
echo   - Conductor端口: %conductorPort%
echo.

REM 创建日志目录
if not exist "logs" mkdir logs

REM 创建临时目录
if not exist "temp" mkdir temp

REM 检查前端依赖
echo 检查前端依赖...
echo Checking frontend dependencies...

if not exist "app\node_modules" (
    echo ✗ 前端依赖未安装，正在安装...
    echo ✗ Frontend dependencies not installed, installing...
    echo.
    
    cd app
    echo   执行: pnpm install
    call pnpm install
    
    if errorlevel 1 (
        echo ✗ 依赖安装失败！
        echo ✗ Dependency installation failed!
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo ✓ 依赖安装完成
) else (
    echo ✓ 前端依赖已安装
)
echo.

echo 正在启动 Moss AI 本地开发环境...
echo Starting Moss AI Local Development Environment...
echo.

REM 步骤1: 启动后端服务
echo [1/6] 启动后端服务 (端口 %backendPort%)...
echo [1/6] Starting Backend Service (Port %backendPort%)...
start "Backend Service" /min cmd /k "cd /d %CD%\app\backend-python && python main.py"
timeout /t 3 /nobreak >nul
echo   ✓ 后端服务已启动
echo   ✓ Backend service started
echo.

REM 步骤2: 启动总管理代理 (Conductor)
echo [2/6] 启动总管理代理 (端口 %conductorPort%)...
echo [2/6] Starting Conductor Agent (Port %conductorPort%)...
start "Conductor Agent" /min cmd /k "cd /d %CD%\agents\conductor_agent && python main.py"
timeout /t 3 /nobreak >nul
echo   ✓ 总管理代理已启动
echo   ✓ Conductor agent started
echo.

REM 步骤3: 启动空调代理
echo [3/6] 启动空调代理 (端口 %airCondPort%)...
echo [3/6] Starting Air Conditioner Agent (Port %airCondPort%)...
start "Air Conditioner Agent" /min cmd /k "cd /d %CD%\agents\air_conditioner_agent && python main.py"
timeout /t 2 /nobreak >nul
echo   ✓ 空调代理已启动
echo.

REM 步骤4: 启动空气净化器代理
echo [4/6] 启动空气净化器代理 (端口 %airCleanPort%)...
echo [4/6] Starting Air Cleaner Agent (Port %airCleanPort%)...
start "Air Cleaner Agent" /min cmd /k "cd /d %CD%\agents\air_cleaner_agent && python main.py"
timeout /t 2 /nobreak >nul
echo   ✓ 空气净化器代理已启动
echo.

REM 步骤5: 启动床头灯代理
echo [5/6] 启动床头灯代理 (端口 %bedsideLampPort%)...
echo [5/6] Starting Bedside Lamp Agent (Port %bedsideLampPort%)...
start "Bedside Lamp Agent" /min cmd /k "cd /d %CD%\agents\bedside_lamp_agent && python main.py"
timeout /t 2 /nobreak >nul
echo   ✓ 床头灯代理已启动
echo.

REM 步骤6: 启动前端开发服务器
echo [6/6] 启动前端开发服务器 (端口 %frontendPort%)...
echo [6/6] Starting Frontend Dev Server (Port %frontendPort%)...
cd /d app
start "Frontend Dev Server" /min cmd /k "pnpm dev"
cd ..
timeout /t 3 /nobreak >nul
echo   ✓ 前端服务已启动
echo   ✓ Frontend service started
echo   提示: 所有服务窗口已最小化到任务栏
echo.

echo.
echo ========================================
echo 所有服务已启动完成！
echo All services started successfully!
echo ========================================
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    服务地址 / Service URLs                  ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                                                            ║
echo ║  【前端应用 / Frontend】                                     ║
echo ║    http://localhost:%frontendPort%
echo ║    ★ 请在浏览器中打开此地址使用应用                           ║
echo ║                                                            ║
echo ║  【后端服务 / Backend】                                      ║
echo ║    http://localhost:%backendPort%
echo ║                                                            ║
echo ║  【智能代理 / Agents】                                       ║
echo ║    总管理代理 / Conductor:      http://localhost:%conductorPort%
echo ║    空调代理 / Air Conditioner:  http://localhost:%airCondPort%
echo ║    空气净化器 / Air Cleaner:    http://localhost:%airCleanPort%
echo ║    床头灯 / Bedside Lamp:       http://localhost:%bedsideLampPort%
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
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
for %%p in (%frontendPort% %backendPort% %conductorPort% %airCondPort% %airCleanPort% %bedsideLampPort%) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr "LISTENING" 2^>nul') do (
        echo 停止端口 %%p 的进程 (PID: %%a)
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo.
echo 所有服务已停止
echo All services stopped
timeout /t 2 /nobreak >nul
