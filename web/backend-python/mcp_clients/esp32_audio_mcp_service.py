"""
ESP32 / Arduino 音频 MCP（stdio）客户端
通过配置与 Cursor 中 esp32_arduino 等 MCP 的 command/args 对齐，以插件方式接入对话 Agent。
"""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import struct
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


def _sine_test_pcm_s16le(
    sample_rate: int, duration_ms: int, freq_hz: float, channels: int
) -> bytes:
    """生成短段 s16le 正弦测试音（多声道为交错相同采样）。"""
    n = max(1, int(sample_rate * duration_ms / 1000))
    ch = max(1, min(2, int(channels)))
    out = bytearray()
    for i in range(n):
        s = int(32767 * 0.22 * math.sin(2 * math.pi * freq_hz * i / sample_rate))
        for _ in range(ch):
            out.extend(struct.pack("<h", s))
    return bytes(out)


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
                "message": "ESP32 音频 MCP 未启用。请在「账户 → 插件扩展 → 音频/ESP32」中启用并填写 command/args，"
                "或在环境变量中设置 MOSS_ESP32_AUDIO_MCP_ENABLED=1（并配置 command/args）。",
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
                "message": "ESP32 音频 MCP 未启用。请在「账户 → 插件扩展 → 音频/ESP32」中启用并填写 command/args，"
                "或设置 MOSS_ESP32_AUDIO_MCP_* 环境变量。",
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

    async def test_speaker_output(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        duration_ms: int = 400,
        freq_hz: float = 440.0,
        tool_name_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        列出 MCP 工具并调用扬声器播放类工具，下发一段短测试 PCM（与固件 esp32_audio_speaker_play_pcm 等兼容）。
        """
        listed = await self.list_mcp_tools()
        if not listed.get("success"):
            return {
                "success": False,
                "message": str(listed.get("message") or "无法列出 MCP 工具"),
                "tool_name": None,
                "mcp": listed,
            }
        tools = listed.get("tools") or []
        names = [str(t.get("name") or "") for t in tools if t.get("name")]

        tool_name: Optional[str] = None
        override = (tool_name_override or "").strip()
        if override:
            if override in names:
                tool_name = override
            else:
                return {
                    "success": False,
                    "message": f"未找到指定工具「{override}」。当前可用: {', '.join(names) or '无'}",
                    "tool_name": None,
                    "mcp": {"tools": names},
                }
        else:
            for n in names:
                if n == "esp32_audio_speaker_play_pcm":
                    tool_name = n
                    break
            if not tool_name:
                for n in names:
                    nl = n.lower()
                    if "speaker" in nl and ("play" in nl or "pcm" in nl):
                        tool_name = n
                        break
            if not tool_name:
                return {
                    "success": False,
                    "message": "未找到扬声器播放类工具（例如 esp32_audio_speaker_play_pcm）。"
                    "请确认 MCP 已启动且 tools/list 中包含播音工具。",
                    "tool_name": None,
                    "mcp": {"tools": names},
                }

        pcm = _sine_test_pcm_s16le(sample_rate, duration_ms, freq_hz, channels)
        b64 = base64.b64encode(pcm).decode("ascii")
        arguments: Dict[str, Any] = {
            "pcm_base64": b64,
            "sample_rate": sample_rate,
            "channels": channels,
        }
        out = await self.call_tool(tool_name, arguments)
        if not out.get("success"):
            return {
                "success": False,
                "message": str(out.get("message") or "调用 MCP 播音工具失败"),
                "tool_name": tool_name,
                "mcp": out,
            }
        return {
            "success": True,
            "message": f"已下发测试音（约 {duration_ms / 1000:.1f} 秒、{int(freq_hz)}Hz）；"
            "若扬声器与固件正常，应能听到提示音。",
            "tool_name": tool_name,
            "mcp": out,
        }


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
