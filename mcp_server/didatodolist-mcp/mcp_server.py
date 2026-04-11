"""
滴答清单 MCP 服务器定义
"""

import os
import dotenv
from functools import wraps
from fastmcp import FastMCP
# 尝试导入可能的 AuthError，如果不存在也没关系
try:
    # 假设 fastmcp 提供了特定的认证错误类型
    from fastmcp import AuthError
except ImportError:
    # 如果没有，使用内置的 PermissionError 作为备选
    AuthError = PermissionError

# 导入工具模块
from tools.task_tools import register_task_tools
from tools.project_tools import register_project_tools
from tools.tag_tools import register_tag_tools
from tools.analytics_tools import register_analytics_tools
from tools.goal_tools import register_goal_tools
from tools.official_api import APIError, init_api
from utils.asgi_auth import with_api_key_auth

# 载入 .env（若存在）
dotenv.load_dotenv()

# --- 鉴权逻辑 ---
EXPECTED_API_KEY = os.environ.get("MCP_API_KEY", "123") # 从环境变量获取，默认'123'

def authenticate_request(context: dict):
    """
    认证回调函数，尝试检查 API Key。

    Args:
        context: 一个包含请求或会话信息的字典 (假设 fastmcp 提供)。
                 我们需要这个 context 包含访问请求头的方式。

    Returns:
        认证成功时返回会话数据 (例如用户ID)。

    Raises:
        AuthError: 如果认证失败。
    """
    # !!! 关键点：如何从 context 中获取请求头？ !!!
    # 假设 context 中有一个 'request' 对象，或者直接有 'headers'
    request_headers = context.get("headers", {}) # 这只是一个猜测！
    api_key = request_headers.get("x-api-key") # 同样是猜测！

    # 尝试认证（日志已禁用）
    
    if api_key != EXPECTED_API_KEY:
        # 认证失败：API Key 无效或缺失
        # 抛出认证错误，告知客户端未授权
        raise AuthError("Unauthorized: Invalid API Key") # 或者 PermissionError

    # 认证成功
    # 认证成功，返回需要在会话中存储的数据
    # 这个数据可以在工具函数的 context.session 中访问
    return {
        "authenticated_user_id": "system", # 可以是任何你想存储的信息
        "auth_method": "api_key"
    }


def create_server(auth_info=None):
    """
    创建并配置MCP服务器

    Args:
        auth_info: 认证信息字典（已弃用，token现在通过环境变量传递）

    Returns:
        配置好的MCP服务器实例
    """
    # 注意：不再强制要求.env中的token，因为我们的架构中token从数据库获取并通过env_vars传递
    # 如果环境变量中有token，尝试初始化（用于独立运行场景）
    try:
        if os.environ.get("DIDA_ACCESS_TOKEN"):
            init_api()
            # 已初始化官方API 客户端（从环境变量）
        else:
            # 提示：未检测到 DIDA_ACCESS_TOKEN 环境变量
            # 在集成模式下，token将由调用方通过环境变量传递
            pass
    except Exception as e:
        # 提示：官方API初始化跳过（集成模式下正常）
        pass

    try:
        # 创建FastMCP服务器（简化版，不使用authenticate参数）
        server = FastMCP(
            name="didatodolist-mcp",
            instructions="滴答清单MCP服务，允许AI模型通过MCP协议操作滴答清单待办事项。"
        )

        # 注册所有工具
        register_task_tools(server, auth_info or {})
        register_project_tools(server, auth_info or {})
        register_tag_tools(server, auth_info or {})
        register_analytics_tools(server, auth_info or {})
        register_goal_tools(server, auth_info or {})

        # ✅ 滴答清单MCP服务初始化成功
        return server

    except Exception as e:
        # ❌ 初始化MCP服务器失败
        import traceback
        # traceback.print_exc()  # 禁用traceback输出，避免干扰JSONRPC
        raise

# --- 主程序入口 (示例) ---
if __name__ == "__main__":
    # 从环境变量或配置文件加载认证信息
    dida_auth = {
        "token": os.environ.get("DIDA_TOKEN"),
        # "email": os.environ.get("DIDA_EMAIL"),
        # "password": os.environ.get("DIDA_PASSWORD"),
    }

    if not dida_auth.get("token"):
         print("错误：请设置 DIDA_TOKEN 环境变量")
         exit(1)

    if not os.environ.get("MCP_API_KEY"):
        print("警告：未设置 MCP_API_KEY 环境变量，将使用默认值 '123'")
    else:
        print(f"MCP_API_KEY 已设置为: {EXPECTED_API_KEY}")


    try:
        mcp_server = create_server(dida_auth)
        # 这里需要根据 fastmcp 的文档来正确运行服务器
        print("\n服务器对象已创建。请根据 fastmcp 文档运行服务器。")
        print("例如: python -m fastmcp serve your_module:mcp_server --port 3000")
        # import uvicorn
        # uvicorn.run(mcp_server.app, host="0.0.0.0", port=3000) # 这行可能不正确
    except Exception as e:
         print(f"启动服务器时出错: {e}")