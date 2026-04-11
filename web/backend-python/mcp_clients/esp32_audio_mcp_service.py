"""
ESP32 / Arduino 音频 MCP（stdio）客户端
通过配置与 Cursor 中 esp32_arduino 等 MCP 的 command/args 对齐，以插件方式接入对话 Agent。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ENV_ENABLED = "MOSS_ESP32_AUDIO_MCP_ENABLED"
_ENV_COMMAND = "MOSS_ESP32_AUDIO_MCP_COMMAND"
_ENV_ARGS = "MOSS_ESP32_AUDIO_MCP_ARGS"
_ENV_CWD = "MOSS_ESP32_AUDIO_MCP_CWD"
_ENV_ENV_JSON = "MOSS_ESP32_AUDIO_MCP_ENV_JSON"


def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[3]


def _load_yaml_esp32_section() -> Dict[str, Any]:
    root = _find_project_root()
    for candidate in (root / "config.yaml", root.parent / "config.yaml"):
        if not candidate.exists():
            continue
        try:
            import yaml

            with open(candidate, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            section = data.get("esp32_audio_mcp") or {}
            return section if isinstance(section, dict) else {}
        except Exception as e:
            logger.warning("读取 esp32_audio_mcp 配置失败: %s", e)
    return {}


def _parse_args(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
        return s.split()
    return []


class Esp32AudioMCPService:
    """通过 stdio 连接本机已实现的 MCP 服务（与 Cursor MCP 启动方式一致）。"""

    def __init__(self, yaml_config: Optional[Dict[str, Any]] = None):
        self._yaml = yaml_config if yaml_config is not None else _load_yaml_esp32_section()

    def _merged_config(self) -> Dict[str, Any]:
        y = dict(self._yaml)
        if os.environ.get(_ENV_ENABLED) is not None:
            y["enabled"] = os.environ[_ENV_ENABLED].strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
        if os.environ.get(_ENV_COMMAND):
            y["command"] = os.environ[_ENV_COMMAND].strip()
        if os.environ.get(_ENV_ARGS):
            y["args"] = _parse_args(os.environ[_ENV_ARGS])
        if os.environ.get(_ENV_CWD):
            y["cwd"] = os.environ[_ENV_CWD].strip()
        if os.environ.get(_ENV_ENV_JSON):
            try:
                extra = json.loads(os.environ[_ENV_ENV_JSON])
                if isinstance(extra, dict):
                    y["env"] = {str(k): str(v) for k, v in extra.items()}
            except json.JSONDecodeError:
                logger.warning("MOSS_ESP32_AUDIO_MCP_ENV_JSON 不是合法 JSON，已忽略")
        return y

    @property
    def enabled(self) -> bool:
        c = self._merged_config()
        return bool(c.get("enabled", False))

    def _stdio_params(self):
        from mcp import StdioServerParameters

        c = self._merged_config()
        command = (c.get("command") or "").strip()
        args = _parse_args(c.get("args"))
        if not command:
            return None, "未配置 esp32_audio_mcp.command（或环境变量 MOSS_ESP32_AUDIO_MCP_COMMAND）"

        cwd = c.get("cwd")
        cwd_path = Path(cwd).expanduser() if cwd else None

        env = os.environ.copy()
        extra_env = c.get("env")
        if isinstance(extra_env, dict):
            env.update({str(k): str(v) for k, v in extra_env.items()})

        params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
            cwd=str(cwd_path) if cwd_path else None,
        )
        return params, None

    def _check_mcp_available(self) -> bool:
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client

            _ = (ClientSession, stdio_client)
            return True
        except ImportError as e:
            logger.error("MCP Python SDK 未安装: %s", e)
            return False

    async def list_mcp_tools(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "ESP32 音频 MCP 未启用。请在 config.yaml 的 esp32_audio_mcp.enabled 设为 true，"
                "或设置 MOSS_ESP32_AUDIO_MCP_ENABLED=1，并配置 command/args。",
            }
        if not self._check_mcp_available():
            return {"success": False, "message": "请安装 MCP 客户端依赖：pip install mcp"}

        params, err = self._stdio_params()
        if err:
            return {"success": False, "message": err}

        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    tools = []
                    for t in getattr(listed, "tools", None) or []:
                        tools.append(
                            {
                                "name": getattr(t, "name", ""),
                                "description": getattr(t, "description", "") or "",
                            }
                        )
                    return {"success": True, "tools": tools}
        except Exception as e:
            logger.exception("列出 ESP32 MCP 工具失败")
            return {"success": False, "message": str(e)}

    async def call_tool(
        self, tool_name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "ESP32 音频 MCP 未启用。请配置 config.yaml 或 MOSS_ESP32_AUDIO_MCP_* 环境变量。",
            }
        if not self._check_mcp_available():
            return {"success": False, "message": "请安装 MCP 客户端依赖：pip install mcp"}

        params, err = self._stdio_params()
        if err:
            return {"success": False, "message": err}

        arguments = arguments or {}

        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    chunks: List[str] = []
                    if hasattr(result, "content") and result.content:
                        for block in result.content:
                            if hasattr(block, "text") and block.text:
                                chunks.append(block.text)
                    text = "\n".join(chunks) if chunks else str(result)
                    try:
                        data = json.loads(text)
                        return {"success": True, "data": data}
                    except json.JSONDecodeError:
                        return {"success": True, "data": text}
        except Exception as e:
            logger.exception("调用 ESP32 MCP 工具失败: %s", tool_name)
            return {"success": False, "message": str(e)}


_esp32_audio_mcp_service: Optional[Esp32AudioMCPService] = None


def get_esp32_audio_mcp_service(
    yaml_config: Optional[Dict[str, Any]] = None,
) -> Esp32AudioMCPService:
    global _esp32_audio_mcp_service
    if _esp32_audio_mcp_service is None:
        _esp32_audio_mcp_service = Esp32AudioMCPService(yaml_config=yaml_config)
    elif yaml_config is not None:
        _esp32_audio_mcp_service = Esp32AudioMCPService(yaml_config=yaml_config)
    return _esp32_audio_mcp_service
