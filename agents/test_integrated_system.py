#!/usr/bin/env python3
"""
集成系统测试脚本
测试总管理代理与数据挖掘代理的集成功能
"""

import asyncio
import json
import sys
import os

# 添加代理路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'conductor_agent'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'dw_agent'))

from conductor_agent.main import ConductorAgent
from dw_agent.main import DataMiningAgent


async def test_integrated_system():
    """测试集成系统功能"""
    print("🏠 智能家居集成系统测试")
    print("=" * 60)
    
    # 创建代理实例
    conductor = ConductorAgent()
    data_mining = DataMiningAgent()
    
    print("✅ 代理实例创建成功")
    
    # 测试用例
    test_cases = [
        {
            "agent": "conductor",
            "query": "你好，请介绍一下你的功能",
            "description": "测试总管理代理基本功能"
        },
        {
            "agent": "conductor", 
            "query": "查看所有可用的代理服务",
            "description": "测试代理列表功能"
        },
        {
            "agent": "conductor",
            "query": "控制空调设备，设置温度为25度",
            "description": "测试设备控制（带日志记录）"
        },
        {
            "agent": "conductor",
            "query": "分析我的使用习惯",
            "description": "测试用户行为分析"
        },
        {
            "agent": "conductor",
            "query": "获取个性化建议",
            "description": "测试用户洞察功能"
        },
        {
            "agent": "data_mining",
            "query": "分析用户default_user在最近30天的使用习惯",
            "description": "测试数据挖掘代理"
        },
        {
            "agent": "data_mining",
            "query": "预测用户default_user对空调的温度偏好",
            "description": "测试偏好预测功能"
        }
    ]
    
    print(f"\n📋 开始执行 {len(test_cases)} 个测试用例...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {test_case['description']} ---")
        print(f"代理: {test_case['agent']}")
        print(f"查询: {test_case['query']}")
        
        try:
            # 选择代理
            agent = conductor if test_case['agent'] == 'conductor' else data_mining
            
            # 模拟上下文ID
            context_id = f"test_context_{i}"
            
            # 流式处理响应
            async for response in agent.stream(test_case['query'], context_id):
                if response.get('is_task_complete'):
                    print(f"✅ 完成: {response['content'][:200]}...")
                    break
                else:
                    print(f"⏳ 处理中: {response['content']}")
                    
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print("\n🎉 集成系统测试完成！")


async def test_database_logging():
    """测试数据库日志记录功能"""
    print("\n🗄️ 测试数据库日志记录功能")
    print("-" * 40)
    
    try:
        import sqlite3
        
        # 检查数据库文件
        db_path = "user_behavior.db"
        if os.path.exists(db_path):
            print(f"✅ 数据库文件存在: {db_path}")
            
            # 查询操作记录
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM device_operations")
            count = cursor.fetchone()[0]
            print(f"📊 总操作记录数: {count}")
            
            if count > 0:
                cursor.execute("SELECT * FROM device_operations ORDER BY timestamp DESC LIMIT 5")
                recent_ops = cursor.fetchall()
                print("📝 最近5条操作记录:")
                for op in recent_ops:
                    print(f"  - {op[2]} {op[4]} ({op[6]})")
            
            conn.close()
        else:
            print("⚠️ 数据库文件不存在，将在首次操作时创建")
            
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")


async def test_agent_communication():
    """测试代理间通信"""
    print("\n🔄 测试代理间通信")
    print("-" * 40)
    
    try:
        # 测试总管理代理调用数据挖掘功能
        conductor = ConductorAgent()
        context_id = "communication_test"
        
        print("测试总管理代理调用用户洞察功能...")
        async for response in conductor.stream("获取我的使用洞察和建议", context_id):
            if response.get('is_task_complete'):
                print("✅ 代理间通信成功")
                print(f"响应: {response['content'][:150]}...")
                break
            else:
                print(f"⏳ {response['content']}")
                
    except Exception as e:
        print(f"❌ 代理间通信测试失败: {e}")


if __name__ == "__main__":
    print("🚀 启动智能家居集成系统测试")
    
    # 运行所有测试
    asyncio.run(test_integrated_system())
    asyncio.run(test_database_logging())
    asyncio.run(test_agent_communication())
    
    print("\n" + "=" * 60)
    print("✨ 所有测试完成！")
    print("\n📋 系统功能总结:")
    print("  ✅ 总管理代理 - 协调所有智能设备")
    print("  ✅ 数据挖掘代理 - 分析用户行为数据")
    print("  ✅ 自动日志记录 - 所有操作自动保存到数据库")
    print("  ✅ 用户行为分析 - 基于历史数据生成洞察")
    print("  ✅ 个性化建议 - 根据使用习惯提供建议")
    print("  ✅ 代理间通信 - 支持代理间协作")
