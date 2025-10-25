# 测试聊天集成功能
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   Moss AI 聊天集成测试" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 测试 1: Conductor Agent (A2A Server)
Write-Host "[测试 1/3] 检查 Conductor Agent (A2A Server, 端口 12000)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:12000/" -Method Get -TimeoutSec 5
    Write-Host "✓ Conductor Agent (A2A) 运行正常" -ForegroundColor Green
    if ($response.name) {
        Write-Host "  Agent: $($response.name)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Conductor Agent 未响应" -ForegroundColor Red
    Write-Host "  请确保已启动: python agents/conductor_agent/main.py --host localhost --port 12000" -ForegroundColor Yellow
}

Write-Host ""

# 测试 2: Cangjie 后端 API
Write-Host "[测试 2/3] 检查 Cangjie 后端 API (端口 2100)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:2100/hello" -Method Get -TimeoutSec 5
    Write-Host "✓ Cangjie 后端运行正常" -ForegroundColor Green
    Write-Host "  响应: name=$($response.name), age=$($response.age)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Cangjie 后端未响应" -ForegroundColor Red
    Write-Host "  请确保已启动后端服务" -ForegroundColor Yellow
}

Write-Host ""

# 测试 3: 完整对话流程
Write-Host "[测试 3/3] 测试完整对话流程..." -ForegroundColor Yellow
try {
    $body = @{
        query = "你好，我是测试用户"
        context_id = "test-session-001"
    } | ConvertTo-Json -Compress

    $headers = @{
        "Content-Type" = "application/json"
    }

    Write-Host "  发送测试消息: '你好，我是测试用户'" -ForegroundColor Gray
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:2100/api/chat" -Method Post -Body $body -Headers $headers -TimeoutSec 30
    
    Write-Host "✓ 对话流程测试成功" -ForegroundColor Green
    Write-Host "  AI 回复: $($response.content)" -ForegroundColor Gray
} catch {
    Write-Host "✗ 对话流程测试失败" -ForegroundColor Red
    Write-Host "  错误: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   测试完成" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 打开浏览器访问 http://localhost:5173" -ForegroundColor White
Write-Host "  2. 导航到聊天页面" -ForegroundColor White
Write-Host "  3. 尝试发送消息测试对话功能" -ForegroundColor White
Write-Host ""

Read-Host "按 Enter 键退出"

