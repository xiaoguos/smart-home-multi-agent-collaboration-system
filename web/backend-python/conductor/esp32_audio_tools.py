"""
ESP32 / Arduino 音频 MCP 插件工具（stdio）
与 Cursor 中配置的 esp32_arduino 等 MCP 使用相同的 command/args 即可。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _esp32_mcp_yaml_config() -> Dict[str, Any]:
    """优先数据库 plugin.audio.mcp_config，否则 config.yaml。"""
    from conductor.config_loader import get_config_loader

    return get_config_loader(strict_mode=False).get_esp32_audio_mcp_config()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Esp32AudioMcpListArgs(BaseModel):
    """列出远端 MCP 已注册的工具（名称与 Cursor 中一致）。"""


class Esp32AudioMcpInvokeArgs(BaseModel):
    tool_name: str = Field(
        ...,
        description="MCP 工具名，须与 list_esp32_audio_mcp_tools 或 Cursor MCP 中列出的名称一致",
    )
    arguments_json: Optional[str] = Field(
        default=None,
        description='JSON 字符串，作为该工具的参数对象，例如 {} 或 {"key":"value"}；无参数可省略或写 "{}"',
    )


@tool(
    "list_esp32_audio_mcp_tools",
    args_schema=Esp32AudioMcpListArgs,
    description="列出当前配置的 ESP32/Arduino 音频 MCP 所提供的工具名称与说明；"
    "用户要做录音、播放、串口音频等硬件相关操作前，可先调用本工具确认可用工具名。",
)
def list_esp32_audio_mcp_tools() -> str:
    try:
        _ensure_backend_import_path()
        from mcp_clients.esp32_audio_mcp_service import get_esp32_audio_mcp_service

        svc = get_esp32_audio_mcp_service(yaml_config=_esp32_mcp_yaml_config())
        result = _run_async(svc.list_mcp_tools())
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("list_esp32_audio_mcp_tools 失败: %s", e, exc_info=True)
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)


@tool(
    "invoke_esp32_audio_mcp_tool",
    args_schema=Esp32AudioMcpInvokeArgs,
    description="调用已配置的 ESP32 音频 MCP 中的某个工具（stdio）。"
    "tool_name 必须与 MCP 服务端注册名一致；参数用 arguments_json 传递 JSON 对象字符串。",
)
def invoke_esp32_audio_mcp_tool(tool_name: str, arguments_json: Optional[str] = None) -> str:
    args: Dict[str, Any] = {}
    if arguments_json and str(arguments_json).strip():
        try:
            parsed = json.loads(arguments_json)
            if not isinstance(parsed, dict):
                return json.dumps(
                    {
                        "success": False,
                        "message": "arguments_json 必须是 JSON 对象，例如 {\"volume\": 50}",
                    },
                    ensure_ascii=False,
                )
            args = parsed
        except json.JSONDecodeError as e:
            return json.dumps(
                {"success": False, "message": f"arguments_json 解析失败: {e}"},
                ensure_ascii=False,
            )

    try:
        _ensure_backend_import_path()
        from mcp_clients.esp32_audio_mcp_service import get_esp32_audio_mcp_service

        svc = get_esp32_audio_mcp_service(yaml_config=_esp32_mcp_yaml_config())
        result = _run_async(svc.call_tool(tool_name, args))
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("invoke_esp32_audio_mcp_tool 失败: %s", e, exc_info=True)
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)


ESP32_AUDIO_TOOL_NAMES = (
    "list_esp32_audio_mcp_tools",
    "invoke_esp32_audio_mcp_tool",
)
