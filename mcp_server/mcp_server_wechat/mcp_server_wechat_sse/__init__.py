from mcp_server_wechat_sse.WechatServer import WeChatServer

async def serve(default_folder_path=None, host="0.0.0.0", port=3000):
    """启动微信MCP服务器（SSE模式）"""
    server = WeChatServer(default_folder_path=default_folder_path, host=host, port=port)
    await server.serve()

def main():
    """提供微信交互功能的MCP服务器"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="给模型提供微信聊天记录获取和消息发送功能的MCP服务器（SSE模式）"
    )
    parser.add_argument("--folder-path", default="C://Users//Administrator//Documents//mcp_wechat_history",
                        help="默认保存聊天记录的文件夹路径")
    parser.add_argument("--host", default="0.0.0.0",
                        help="SSE服务器监听地址（默认：0.0.0.0）")
    parser.add_argument("--port", type=int, default=3000,
                        help="SSE服务器监听端口（默认：3000）")
    args = parser.parse_args()

    asyncio.run(serve(
        default_folder_path=args.folder_path,
        host=args.host,
        port=args.port
    ))

if __name__ == "__main__":
    main()
