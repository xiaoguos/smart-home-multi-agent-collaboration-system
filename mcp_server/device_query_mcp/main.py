"""
MCP Gateway Server

Expose a unified MCP server that can proxy calls to other MCP services.

Default downstream services:
- device_query: mcp_server/device_query_mcp.py
- dida_todolist: mcp_server/didatodolist-mcp/main.py
- wechat: mcp_server/mcp_server_wechat/mcp_server_wechat/__main__.py

Optional environment overrides:
- MCP_GATEWAY_PYTHON: python executable path
- MCP_GATEWAY_SERVICES_JSON: JSON object to override/add services
  Example:
  {
    "my_service": {
      "command": "python",
      "args": ["D:/path/to/server.py"],
      "cwd": "D:/path/to",
      "env": {"FOO": "bar"}
    }
  }
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("MCP Gateway", version="1.0.0")

MCP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MCP_DIR.parent


def _python_cmd() -> str:
    return os.environ.get("MCP_GATEWAY_PYTHON", sys.executable or "python")


def _default_services() -> dict[str, dict[str, Any]]:
    return {
        "device_query": {
            "command": _python_cmd(),
            "args": [str(MCP_DIR / "device_query_mcp.py")],
            "cwd": str(PROJECT_ROOT),
            "env": {},
        },
        "dida_todolist": {
            "command": _python_cmd(),
            "args": [str(MCP_DIR / "didatodolist-mcp" / "main.py")],
            "cwd": str(MCP_DIR / "didatodolist-mcp"),
            "env": {},
        },
        "wechat": {
            "command": _python_cmd(),
            "args": [str(MCP_DIR / "mcp_server_wechat" / "mcp_server_wechat" / "__main__.py")],
            "cwd": str(MCP_DIR / "mcp_server_wechat"),
            "env": {
                "PYTHONPATH": str(MCP_DIR / "mcp_server_wechat"),
            },
        },
    }


def _safe_model_dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json", exclude_none=True)
        except Exception:
            return str(obj)
    return str(obj)


def _normalize_service_cfg(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    command = str(cfg.get("command", "")).strip()
    if not command:
        raise ValueError(f"service '{name}' missing command")

    args_raw = cfg.get("args", [])
    if not isinstance(args_raw, list):
        raise ValueError(f"service '{name}' args must be a list")
    args = [str(x) for x in args_raw]

    cwd = cfg.get("cwd")
    cwd_str = str(cwd).strip() if cwd else None

    env_raw = cfg.get("env", {})
    if env_raw is None:
        env_raw = {}
    if not isinstance(env_raw, dict):
        raise ValueError(f"service '{name}' env must be an object")
    env = {str(k): str(v) for k, v in env_raw.items()}

    return {
        "command": command,
        "args": args,
        "cwd": cwd_str,
        "env": env,
    }


def _load_services() -> dict[str, dict[str, Any]]:
    services = _default_services()
    raw = os.environ.get("MCP_GATEWAY_SERVICES_JSON")
    if not raw:
        return {k: _normalize_service_cfg(k, v) for k, v in services.items()}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("MCP_GATEWAY_SERVICES_JSON is not valid JSON: %s", e)
        return {k: _normalize_service_cfg(k, v) for k, v in services.items()}

    if not isinstance(parsed, dict):
        logger.error("MCP_GATEWAY_SERVICES_JSON must be a JSON object")
        return {k: _normalize_service_cfg(k, v) for k, v in services.items()}

    merged = dict(services)
    for key, value in parsed.items():
        if isinstance(value, dict):
            merged[str(key)] = value
        else:
            logger.warning("Skip invalid service '%s': config must be object", key)

    return {k: _normalize_service_cfg(k, v) for k, v in merged.items()}


SERVICES = _load_services()


def _ensure_service_exists(service_name: str) -> tuple[bool, str]:
    if service_name in SERVICES:
        return True, ""
    supported = ", ".join(sorted(SERVICES.keys()))
    return False, f"unknown service '{service_name}', supported: {supported}"


def _parse_arguments(arguments_json: str) -> tuple[bool, dict[str, Any] | str]:
    if not arguments_json.strip():
        return True, {}
    try:
        parsed = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        return False, f"arguments_json is invalid JSON: {e}"
    if not isinstance(parsed, dict):
        return False, "arguments_json must be a JSON object"
    return True, parsed


async def _open_session(service_name: str):
    cfg = SERVICES[service_name]
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env.update(cfg["env"])

    params = StdioServerParameters(
        command=cfg["command"],
        args=cfg["args"],
        cwd=cfg["cwd"],
        env=env,
    )
    return ClientSession, stdio_client, params


def _parse_call_result(result: Any) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    text_chunks: list[str] = []
    for part in getattr(result, "content", []) or []:
        text = getattr(part, "text", None)
        if isinstance(text, str):
            parts.append({"type": "text", "text": text})
            text_chunks.append(text)
        else:
            parts.append({"type": "other", "data": _safe_model_dump(part)})

    joined = "\n".join(text_chunks).strip()
    parsed_text: Any = None
    if joined:
        try:
            parsed_text = json.loads(joined)
        except json.JSONDecodeError:
            parsed_text = joined

    return {
        "parts": parts,
        "text": joined,
        "parsed": parsed_text,
        "raw": _safe_model_dump(result),
    }


@mcp.tool()
def list_gateway_services() -> str:
    """List downstream MCP services configured in the gateway."""
    items = []
    for name, cfg in sorted(SERVICES.items(), key=lambda x: x[0]):
        items.append(
            {
                "service_name": name,
                "command": cfg["command"],
                "args": cfg["args"],
                "cwd": cfg["cwd"],
                "env_keys": sorted(cfg["env"].keys()),
            }
        )

    return json.dumps(
        {
            "success": True,
            "services": items,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def list_gateway_service_tools(service_name: str) -> str:
    """List all tools exposed by one downstream MCP service."""
    ok, msg = _ensure_service_exists(service_name)
    if not ok:
        return json.dumps({"success": False, "message": msg}, ensure_ascii=False, indent=2)

    try:
        ClientSession, stdio_client, params = await _open_session(service_name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = []
                for t in getattr(listed, "tools", []) or []:
                    tools.append(
                        {
                            "name": getattr(t, "name", ""),
                            "description": getattr(t, "description", "") or "",
                            "input_schema": getattr(t, "inputSchema", None),
                        }
                    )

        return json.dumps(
            {"success": True, "service_name": service_name, "tools": tools},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        logger.exception("list tools failed: %s", service_name)
        return json.dumps(
            {"success": False, "service_name": service_name, "message": str(e)},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
async def call_gateway_service_tool(
    service_name: str,
    tool_name: str,
    arguments_json: str = "{}",
) -> str:
    """
    Call a downstream MCP tool through the gateway.

    - service_name: target service in the gateway
    - tool_name: target tool name
    - arguments_json: JSON object string, such as {"system_user_id":1000000001}
    """
    ok, msg = _ensure_service_exists(service_name)
    if not ok:
        return json.dumps({"success": False, "message": msg}, ensure_ascii=False, indent=2)

    ok, args_or_msg = _parse_arguments(arguments_json)
    if not ok:
        return json.dumps({"success": False, "message": args_or_msg}, ensure_ascii=False, indent=2)
    arguments = args_or_msg

    try:
        ClientSession, stdio_client, params = await _open_session(service_name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)

        parsed = _parse_call_result(result)
        return json.dumps(
            {
                "success": True,
                "service_name": service_name,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": parsed,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        logger.exception("call tool failed: %s/%s", service_name, tool_name)
        return json.dumps(
            {
                "success": False,
                "service_name": service_name,
                "tool_name": tool_name,
                "arguments": arguments,
                "message": str(e),
            },
            ensure_ascii=False,
            indent=2,
        )


def _runtime_defaults() -> tuple[str, str, int]:
    transport = os.environ.get("MCP_GATEWAY_TRANSPORT", "sse").strip().lower()
    if transport not in {"sse", "stdio"}:
        logger.warning("Invalid MCP_GATEWAY_TRANSPORT=%s, fallback to sse", transport)
        transport = "sse"

    host = os.environ.get("MCP_GATEWAY_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_raw = os.environ.get("MCP_GATEWAY_PORT", "8099").strip() or "8099"
    try:
        port = int(port_raw)
    except ValueError:
        logger.warning("Invalid MCP_GATEWAY_PORT=%s, fallback to 8099", port_raw)
        port = 8099

    return transport, host, port


def main() -> None:
    env_transport, env_host, env_port = _runtime_defaults()

    parser = argparse.ArgumentParser(description="MCP Gateway Server")
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default=None,
        help="Gateway transport mode (default from env MCP_GATEWAY_TRANSPORT or sse)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="SSE bind host (default from env MCP_GATEWAY_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="SSE bind port (default from env MCP_GATEWAY_PORT or 8099)",
    )
    args = parser.parse_args()

    transport = args.transport or env_transport
    host = args.host or env_host
    port = args.port if args.port is not None else env_port

    if transport == "sse":
        logger.info("Starting MCP Gateway in SSE mode at http://%s:%s", host, port)
        mcp.run(transport="sse", host=host, port=port)
        return

    logger.info("Starting MCP Gateway in stdio mode")
    mcp.run()


if __name__ == "__main__":
    main()
