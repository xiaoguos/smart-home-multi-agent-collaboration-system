#!/usr/bin/env python3
"""
总管理代理测试脚本
用于测试ConductorAgent的基本功能
"""

import asyncio
import json
from main import ConductorAgent


async def test_conductor_agent():
    """测试总管理代理的基本功能"""
    print("🚀 启动总管理代理测试...")
    
    # 创建代理实例
    agent = ConductorAgent()
    print("✅ 代理实例创建成功")
    
    # 测试用例
    test_cases = [
        "你好，请介绍一下你的功能",
        "查看所有可用的代理服务",
        "检查系统状态",
        "获取系统概览",
        "控制空调设备，设置温度为25度",
        "向空调代理发送开启命令"
    ]
    
    print(f"\n📋 开始执行 {len(test_cases)} 个测试用例...")
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {query} ---")
        
        try:
            # 模拟上下文ID
            context_id = f"test_context_{i}"
            
            # 流式处理响应
            async for response in agent.stream(query, context_id):
                if response.get('is_task_complete'):
                    print(f"✅ 完成: {response['content']}")
                    break
                else:
                    print(f"⏳ 处理中: {response['content']}")
                    
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print("\n🎉 测试完成！")


async def test_tools_directly():
    """直接测试工具函数"""
    print("\n🔧 直接测试工具函数...")
    
    from tools import (
        list_available_agents,
        get_agent_status,
        get_system_overview,
        control_device
    )
    
    # 测试列出代理
    print("\n1. 测试列出可用代理:")
    result = list_available_agents()
    print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
    
    # 测试获取代理状态
    print("\n2. 测试获取代理状态:")
    result = get_agent_status()
    print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
    
    # 测试获取系统概览
    print("\n3. 测试获取系统概览:")
    result = get_system_overview()
    print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
    
    # 测试设备控制
    print("\n4. 测试设备控制:")
    result = control_device("air_conditioner", "set_temperature", {"temperature": 25})
    print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    print("🏠 智能家居总管理代理测试")
    print("=" * 50)
    
    # 运行测试
    asyncio.run(test_conductor_agent())
    asyncio.run(test_tools_directly())
    
    print("\n" + "=" * 50)
    print("✨ 所有测试完成！")
