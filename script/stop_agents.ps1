#!/usr/bin/env pwsh
# 停止智能家居代理系统

$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { chcp 65001 > $null } catch { }

function Write-ColorText {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

Clear-Host
Write-ColorText "======================================" "Cyan"
Write-ColorText "停止智能家居代理系统" "Cyan"
Write-ColorText "======================================" "Cyan"
Write-Host ""

$ports = @(12000, 12001, 12002, 12003)
$names = @("空调代理", "空气净化器", "总管理", "数据挖掘")
$stopped = 0

for ($i = 0; $i -lt $ports.Length; $i++) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $ports[$i] -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $conns) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                Write-ColorText "[$($names[$i])] 端口 $($ports[$i]) PID: $($proc.Id)" "Yellow"
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Write-ColorText "  ✓ 已停止" "Green"
                $stopped++
            }
        }
    } catch { }
}

Write-Host ""
Write-ColorText "======================================" "Cyan"
if ($stopped -gt 0) {
    Write-ColorText "✓ 已停止 $stopped 个进程" "Green"
} else {
    Write-ColorText "未找到运行中的代理" "Yellow"
}
Write-ColorText "======================================" "Cyan"
Write-Host ""

