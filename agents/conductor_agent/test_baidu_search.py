"""
测试百度AI搜索工具的集成
"""
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from tools import search_baidu_ai
import json

def test_baidu_search():
    """测试百度AI搜索功能"""
    print("=" * 60)
    print("测试百度AI搜索工具")
    print("=" * 60)
    
    # 测试场景1：睡觉场景
    print("\n【测试1】睡觉场景查询")
    print("-" * 60)
    result1 = search_baidu_ai("人类最适合的睡觉温度和灯光设置")
    print(result1)
    
    # 测试场景2：空调温度
    print("\n【测试2】空调温度查询")
    print("-" * 60)
    result2 = search_baidu_ai("空调最舒适的温度设置")
    print(result2)
    
    # 测试场景3：灯光设置
    print("\n【测试3】灯光设置查询")
    print("-" * 60)
    result3 = search_baidu_ai("睡觉时最适合的灯光亮度")
    print(result3)
    
    # 测试场景4：空气净化器
    print("\n【测试4】空气净化器查询")
    print("-" * 60)
    result4 = search_baidu_ai("空气净化器夜间模式推荐设置")
    print(result4)
    
    # 测试场景5：通用查询
    print("\n【测试5】通用查询")
    print("-" * 60)
    result5 = search_baidu_ai("智能家居最佳设置")
    print(result5)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_baidu_search()

