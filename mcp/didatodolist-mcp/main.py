#!/usr/bin/env python
"""
滴答清单 MCP 服务入口点
允许AI模型通过MCP协议访问和操作滴答清单待办事项
"""

import os
import sys
import argparse
import json
from pathlib import Path
import dotenv
from mcp_server import create_server
from tools.official_api import init_api

# 加载环境变量（支持 .env）
dotenv.load_dotenv()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="滴答清单 MCP 服务"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="安装到Claude Desktop或其他MCP客户端"
    )
    parser.add_argument(
        "--token",
        help="滴答清单访问令牌"
    )
    parser.add_argument(
        "--email",
        help="滴答清单账户邮箱"
    )
    parser.add_argument(
        "--phone",
        help="滴答清单账户手机号"
    )
    parser.add_argument(
        "--password",
        help="滴答清单账户密码"
    )
    # 统一 .env-only，不再支持 config 文件路径
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="服务器端口号（用于SSE传输方式）"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="服务器主机（用于SSE传输方式）"
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="使用SSE传输方式而不是stdio"
    )

    return parser.parse_args()

def ensure_oauth_ready() -> bool:
    """
    检查OAuth是否就绪（仅用于独立运行模式）
    在集成模式下，token由外部传入，所以这个检查是可选的
    """
    try:
        if os.environ.get("DIDA_ACCESS_TOKEN"):
            init_api()
            # ✅ 检测到环境变量中的 OAuth token
            return True
        else:
            # 未检测到 DIDA_ACCESS_TOKEN 环境变量
            # 在集成模式下这是正常的，token将由调用方传递
            return False
    except Exception as e:
        # OAuth初始化警告（在集成模式下正常）
        return False

def main():
    """主函数"""
    args = parse_args()
    # OAuth检查不再是强制性的
    ensure_oauth_ready()

    # 创建MCP服务器
    server = create_server({})

    # 启动服务器
    if args.install:
        # 安装到Claude Desktop
        # 正在安装到MCP客户端...
        os.system("fastmcp install")
    else:
        # 直接运行
        # 启动滴答清单MCP服务器
        if args.sse:
            # 使用SSE传输方式
            server.run(transport="sse", host=args.host, port=args.port)
        else:
            # 使用默认stdio传输方式
            server.run()

if __name__ == "__main__":
    main()