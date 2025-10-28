@echo off
REM 智能家居代理系统启动脚本 (Windows)
REM Smart Home Agent System Startup Script (Windows)
REM 
REM 架构设计：
REM   - 环境检查模块：统一检查所有运行环境
REM   - 配置管理模块：集中处理配置文件读取
REM   - 服务管理模块：统一启动/停止服务
REM   - 工具函数模块：提供可复用的通用功能

setlocal enabledelayedexpansion

REM 设置编码为UTF-8
chcp 65001 >nul

echo ========================================
echo 智能家居代理系统启动脚本
echo Smart Home Agent System Startup Script
echo ========================================
echo.

REM ========================================
REM 主流程
REM ========================================
call :CheckEnvironment
call :LocateProjectRoot
call :LoadConfiguration
call :PrepareDirectories
call :CheckDependencies
call :StartAllServices
call :DisplayServiceInfo
call :WaitForExit
goto :eof

REM ========================================
REM 环境检查模块 - 统一检查所有必要的运行环境
REM ========================================
:CheckEnvironment
echo 检查运行环境...
echo Checking runtime environment...
echo.

call :CheckCommand "python" "Python" "Python 3.8+" "pythonVer"
call :CheckCommand "node" "Node.js" "Node.js 16+" "nodeVer"
call :CheckCommand "pnpm" "pnpm" "npm install -g pnpm" "pnpmVer"
call :CheckCommand "uv" "uv" "pip install uv" "uvVer"
echo.
goto :eof

REM 通用命令检查函数
REM 参数: %1=命令名 %2=显示名 %3=安装提示 %4=版本变量名
:CheckCommand
set "cmd=%~1"
set "name=%~2"
set "install=%~3"
set "verVar=%~4"

%cmd% --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: 未找到%name%
    echo ✗ Error: %name% not found
    echo   请安装: %install%
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%cmd% --version 2^>^&1') do (
    set "%verVar%=%%i"
    goto :version_found
)
:version_found
call echo ✓ %name%: %%%verVar%%%
goto :eof

REM ========================================
REM 项目定位模块 - 自动定位项目根目录
REM ========================================
:LocateProjectRoot
echo 定位项目根目录...
echo Locating project root directory...

set "paths=. .. ..\.."
set "found=0"

for %%p in (%paths%) do (
    if exist "%%p\config.yaml" (
        cd /d "%%p" 2>nul
        set "found=1"
        goto :root_found
    )
)

:root_found
if "%found%"=="0" (
    echo ✗ 错误: 未找到配置文件 config.yaml
    echo ✗ Error: Configuration file config.yaml not found
    echo 当前目录: %CD%
    pause
    exit /b 1
)

echo ✓ 配置文件已找到
echo ✓ Configuration file found: %CD%
echo.
goto :eof

REM ========================================
REM 配置管理模块 - 集中处理配置读取和默认值
REM ========================================
:LoadConfiguration
echo 读取配置文件...
echo Reading configuration file...

REM 定义配置项映射：YAML路径|变量名|默认值
set "configs=backend.python.port|backendPort|3000"
set "configs=%configs% frontend.dev_server.port|frontendPort|1420"
set "configs=%configs% agents.conductor.port|conductorPort|12000"
set "configs=%configs% agents.air_conditioner.port|airCondPort|12001"
set "configs=%configs% agents.air_cleaner.port|airCleanPort|12002"
set "configs=%configs% agents.bedside_lamp.port|bedsideLampPort|12004"

REM 检查PyYAML是否可用
python -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo   注意: PyYAML 未安装，使用默认端口配置
    echo   Note: PyYAML not installed, using default port configuration
    call :SetDefaultPorts
    goto :config_loaded
)

REM 批量读取配置
for %%c in (%configs%) do (
    for /f "tokens=1,2,3 delims=|" %%a in ("%%c") do (
        call :ReadConfigValue "%%a" "%%b" "%%c"
    )
)

:config_loaded
echo ✓ 配置读取完成
echo   - 后端端口 / Backend Port: %backendPort%
echo   - 前端端口 / Frontend Port: %frontendPort%
echo   - Conductor端口: %conductorPort%
echo.
goto :eof

REM 读取单个配置值
REM 参数: %1=YAML路径 %2=变量名 %3=默认值
:ReadConfigValue
set "yamlPath=%~1"
set "varName=%~2"
set "defaultVal=%~3"

REM 构建Python代码，逐层访问YAML配置
set "pythonCmd=import yaml; c=yaml.safe_load(open('config.yaml')); "
set "accessCode=c"
for %%k in (%yamlPath:.= %) do (
    set "accessCode=!accessCode!['%%k']"
)
set "pythonCmd=!pythonCmd! print(!accessCode!)"

REM 执行Python代码并验证结果
for /f "delims=" %%i in ('python -c "!pythonCmd!" 2^>nul') do (
    echo %%i | findstr /r "^[0-9][0-9]*$" >nul
    if not errorlevel 1 (
        set "%varName%=%%i"
        goto :value_set
    )
)
:value_set
REM 如果读取失败，使用默认值
if not defined %varName% set "%varName%=%defaultVal%"
goto :eof

REM 设置默认端口值
:SetDefaultPorts
set "backendPort=3000"
set "frontendPort=1420"
set "conductorPort=12000"
set "airCondPort=12001"
set "airCleanPort=12002"
set "bedsideLampPort=12004"
goto :eof

REM ========================================
REM 目录准备模块 - 创建必要的目录
REM ========================================
:PrepareDirectories
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp
goto :eof

REM ========================================
REM 依赖检查模块 - 检查并安装前端依赖
REM ========================================
:CheckDependencies
echo 检查前端依赖...
echo Checking frontend dependencies...

if not exist "app\node_modules" (
    echo ✗ 前端依赖未安装，正在安装...
    echo ✗ Frontend dependencies not installed, installing...
    echo.
    
    pushd app
    echo   执行: pnpm install
    call pnpm install
    
    if errorlevel 1 (
        echo ✗ 依赖安装失败！
        echo ✗ Dependency installation failed!
        popd
        pause
        exit /b 1
    )
    popd
    echo ✓ 依赖安装完成
) else (
    echo ✓ 前端依赖已安装
)
echo.
goto :eof

REM ========================================
REM 服务启动模块 - 统一管理所有服务启动
REM ========================================
:StartAllServices

echo 正在启动 Moss AI 本地开发环境...
echo Starting Moss AI Local Development Environment...
echo.

REM 定义服务配置：序号|显示名|英文名|目录|启动命令|端口变量|延迟秒数
set "services=1|后端服务|Backend Service|app\backend-python|uv run .|backendPort|3"
set "services=%services% 2|总管理代理|Conductor Agent|agents\conductor_agent|uv run .|conductorPort|3"
set "services=%services% 3|空调代理|Air Conditioner Agent|agents\air_conditioner_agent|uv run .|airCondPort|2"
set "services=%services% 4|空气净化器代理|Air Cleaner Agent|agents\air_cleaner_agent|uv run .|airCleanPort|2"
set "services=%services% 5|床头灯代理|Bedside Lamp Agent|agents\bedside_lamp_agent|uv run .|bedsideLampPort|2"
set "services=%services% 6|前端开发服务器|Frontend Dev Server|app|pnpm dev|frontendPort|3"

REM 批量启动所有服务
for %%s in (%services%) do (
    for /f "tokens=1-7 delims=|" %%a in ("%%s") do (
        call :StartService "%%a" "%%b" "%%c" "%%d" "%%e" "%%f" "%%g"
    )
)

echo   提示: 所有服务窗口已最小化到任务栏
echo   Note: All service windows are minimized to taskbar
echo.
goto :eof

REM 启动单个服务
REM 参数: %1=序号 %2=显示名 %3=英文名 %4=目录 %5=命令 %6=端口变量 %7=延迟
:StartService
set "idx=%~1"
set "nameCN=%~2"
set "nameEN=%~3"
set "dir=%~4"
set "cmd=%~5"
set "portVar=%~6"
set "delay=%~7"

call set "port=%%%portVar%%%"

echo [%idx%/6] 启动%nameCN% (端口 %port%)...
echo [%idx%/6] Starting %nameEN% (Port %port%)...
start "%nameEN%" /min cmd /k "cd /d %CD%\%dir% && %cmd%"
timeout /t %delay% /nobreak >nul
echo   ✓ %nameCN%已启动
echo   ✓ %nameEN% started
echo.
goto :eof

REM ========================================
REM 信息显示模块 - 显示服务地址和使用说明
REM ========================================
:DisplayServiceInfo
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
goto :eof

REM ========================================
REM 退出处理模块 - 等待用户操作并清理资源
REM ========================================
:WaitForExit
echo 提示：关闭此窗口将自动停止所有服务
echo Note: Closing this window will stop all services
echo.
echo 按任意键停止所有服务并退出...
echo Press any key to stop all services and exit...
pause >nul
call :StopAllServices
goto :eof

REM ========================================
REM 服务停止模块 - 统一停止所有服务
REM ========================================
:StopAllServices
echo.
echo 正在停止所有代理服务...
echo Stopping all agent services...
echo.

REM 获取所有需要停止的端口
set "ports=%frontendPort% %backendPort% %conductorPort% %airCondPort% %airCleanPort% %bedsideLampPort%"

REM 批量停止端口对应的进程
for %%p in (%ports%) do (
    call :StopPortProcess %%p
)

echo.
echo ✓ 所有服务已停止
echo ✓ All services stopped
timeout /t 2 /nobreak >nul
goto :eof

REM 停止指定端口的进程
REM 参数: %1=端口号
:StopPortProcess
set "port=%~1"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%port% " ^| findstr "LISTENING" 2^>nul') do (
    echo 停止端口 %port% 的进程 (PID: %%a)
    echo Stopping process on port %port% (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)
goto :eof
