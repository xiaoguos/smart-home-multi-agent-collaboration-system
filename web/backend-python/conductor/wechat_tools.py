"""
微信相关工具
提供微信聊天记录获取和消息发送功能
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class WechatChatHistoryArgs(BaseModel):
    """获取微信聊天记录参数"""
    to_user: str = Field(..., description="好友或群聊的备注或昵称")
    target_date: str = Field(..., description="目标日期，格式为YY/M/D，如25/11/10表示2025年11月10日")


class WechatSendMessageArgs(BaseModel):
    """发送单条消息参数"""
    to_user: str = Field(..., description="好友或群聊的备注或昵称")
    message: str = Field(..., description="要发送的消息内容")


class WechatSendMultipleMessagesArgs(BaseModel):
    """发送多条消息给单个好友参数"""
    to_user: str = Field(..., description="好友或群聊的备注或昵称")
    messages: List[str] = Field(..., description="要发送的消息列表")


class WechatSendToMultipleFriendsArgs(BaseModel):
    """发送消息给多个好友参数"""
    to_users: List[str] = Field(..., description="好友或群聊的备注或昵称列表")
    message: str = Field(..., description="要发送的消息内容（单条消息会发给所有好友）")


@tool("get_wechat_chat_history", args_schema=WechatChatHistoryArgs, description="获取微信特定日期的聊天记录")
def get_wechat_chat_history(
    to_user: str,
    target_date: str
) -> str:
    """
    获取微信聊天记录
    
    Args:
        to_user: 好友或群聊的备注或昵称
        target_date: 目标日期，格式为YY/M/D，如25/11/10
        
    Returns:
        聊天记录的文本描述
    """
    try:
        # 导入MCP服务
        from mcp_clients.wechat_mcp_service import get_wechat_mcp_service
        import asyncio
        
        mcp_service = get_wechat_mcp_service()
        
        # 调用MCP服务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            mcp_service.get_chat_history(to_user, target_date)
        )
        loop.close()
        
        if result and result.get("success"):
            data = result.get("data", "")
            if isinstance(data, str):
                return f"✅ 成功获取与 {to_user} 在 {target_date} 的聊天记录：\n\n{data}"
            else:
                return f"✅ 成功获取聊天记录：\n\n{str(data)}"
        else:
            error_msg = result.get("message", "未知错误") if result else "服务无响应"
            return f"❌ 获取聊天记录失败：{error_msg}\n提示：请确保微信桌面版已登录且窗口可以被操作"
        
    except Exception as e:
        logger.error(f"获取微信聊天记录失败: {e}", exc_info=True)
        return f"❌ 获取微信聊天记录时发生错误：{str(e)}"


@tool("send_wechat_message", args_schema=WechatSendMessageArgs, description="向单个微信好友发送单条消息")
def send_wechat_message(
    to_user: str,
    message: str
) -> str:
    """
    发送单条消息给单个微信好友
    
    Args:
        to_user: 好友或群聊的备注或昵称
        message: 要发送的消息内容
        
    Returns:
        发送结果描述
    """
    try:
        # 导入MCP服务
        from mcp_clients.wechat_mcp_service import get_wechat_mcp_service
        import asyncio
        
        mcp_service = get_wechat_mcp_service()
        
        # 调用MCP服务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            mcp_service.send_message(to_user, message)
        )
        loop.close()
        
        if result and result.get("success"):
            return f"✅ 消息已成功发送给 {to_user}"
        else:
            error_msg = result.get("message", "未知错误") if result else "服务无响应"
            return f"❌ 消息发送失败：{error_msg}\n提示：请确保微信桌面版已登录且窗口可以被操作"
        
    except Exception as e:
        logger.error(f"发送微信消息失败: {e}", exc_info=True)
        return f"❌ 发送微信消息时发生错误：{str(e)}"


@tool("send_multiple_wechat_messages", args_schema=WechatSendMultipleMessagesArgs, description="向单个微信好友发送多条消息")
def send_multiple_wechat_messages(
    to_user: str,
    messages: List[str]
) -> str:
    """
    发送多条消息给单个微信好友
    
    Args:
        to_user: 好友或群聊的备注或昵称
        messages: 要发送的消息列表
        
    Returns:
        发送结果描述
    """
    try:
        # 导入MCP服务
        from mcp_clients.wechat_mcp_service import get_wechat_mcp_service
        import asyncio
        
        mcp_service = get_wechat_mcp_service()
        
        # 调用MCP服务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            mcp_service.send_multiple_messages(to_user, messages)
        )
        loop.close()
        
        if result and result.get("success"):
            return f"✅ 已成功向 {to_user} 发送 {len(messages)} 条消息"
        else:
            error_msg = result.get("message", "未知错误") if result else "服务无响应"
            return f"❌ 批量消息发送失败：{error_msg}\n提示：请确保微信桌面版已登录且窗口可以被操作"
        
    except Exception as e:
        logger.error(f"批量发送微信消息失败: {e}", exc_info=True)
        return f"❌ 批量发送微信消息时发生错误：{str(e)}"


@tool("send_wechat_to_multiple_friends", args_schema=WechatSendToMultipleFriendsArgs, description="向多个微信好友发送消息")
def send_wechat_to_multiple_friends(
    to_users: List[str],
    message: str
) -> str:
    """
    向多个微信好友发送消息
    
    Args:
        to_users: 好友或群聊的备注或昵称列表
        message: 要发送的消息内容（单条消息会发给所有好友）
        
    Returns:
        发送结果描述
    """
    try:
        # 导入MCP服务
        from mcp_clients.wechat_mcp_service import get_wechat_mcp_service
        import asyncio
        
        mcp_service = get_wechat_mcp_service()
        
        # 调用MCP服务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            mcp_service.send_to_multiple_friends(to_users, message)
        )
        loop.close()
        
        if result and result.get("success"):
            return f"✅ 消息已成功发送给 {len(to_users)} 位好友：{', '.join(to_users)}"
        else:
            error_msg = result.get("message", "未知错误") if result else "服务无响应"
            return f"❌ 群发消息失败：{error_msg}\n提示：请确保微信桌面版已登录且窗口可以被操作"
        
    except Exception as e:
        logger.error(f"群发微信消息失败: {e}", exc_info=True)
        return f"❌ 群发微信消息时发生错误：{str(e)}"


# 导出所有工具
__all__ = [
    'get_wechat_chat_history',
    'send_wechat_message',
    'send_multiple_wechat_messages',
    'send_wechat_to_multiple_friends'
]

