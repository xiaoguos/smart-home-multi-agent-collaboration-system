#!/usr/bin/env python3
"""将 main/audio_mcp.c、main/mcp_http.c 补进 compile_commands.json，供 clangd 解析。

从 main.c 复制编译命令，并追加本组件所需头路径（clang 对 @cflags 响应文件支持不完整）。
每次运行会删除旧的 audio_mcp / mcp_http 条目后重新生成。
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional


def idf_root_from_cmd(cmd: str) -> Optional[str]:
    m = re.search(r"-I(\S+?/esp-idf)/components/", cmd)
    if not m:
        return None
    # 捕获组已是 .../esp-idf，勿再拼 /esp-idf（否则变成 .../esp-idf/esp-idf）
    return m.group(1)


def augment_command(cmd: str, source_name: str) -> str:
    """为不同源文件追加 -I，便于 clangd 找到 ringbuf / json / WiFi 等头文件。"""
    root = idf_root_from_cmd(cmd)
    if not root:
        return cmd

    common_mbedtls = [
        "components/mbedtls/mbedtls/include",
        "components/mbedtls/port/include",
        "components/mbedtls/esp_crt_bundle/include",
    ]
    audio_extra = [
        "components/esp_ringbuf/include",
    ] + common_mbedtls

    mcp_extra = audio_extra + [
        "components/json/cJSON",
        "components/esp_http_server/include",
        "components/esp_wifi/include",
        "components/esp_netif/include",
        "components/esp_event/include",
        "components/nvs_flash/include",
        "components/esp-tls",
        "components/esp-tls/esp-tls-crypto",
        "components/http_parser",
        "components/wpa_supplicant/include",
        "components/wpa_supplicant/esp_supplicant/include",
        "components/esp_coex/include",
        "components/lwip/include",
        "components/lwip/include/apps",
        "components/lwip/lwip/src/include",
        "components/lwip/port/include",
        "components/lwip/port/freertos/include",
        "components/lwip/port/esp32xx/include",
    ]

    rels = mcp_extra if source_name == "mcp_http.c" else audio_extra
    parts = []
    for r in rels:
        inc = f"-I{root}/{r}"
        if inc not in cmd:
            parts.append(inc)
    extra = " ".join(parts)
    if not extra:
        return cmd

    if " @\\\"" in cmd:
        return cmd.replace(" @\\\"", f" {extra} @\\\"", 1)
    if ' @"' in cmd:
        return cmd.replace(' @"', f" {extra} @\"", 1)
    return f"{cmd} {extra}"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: patch_compile_commands.py <build/compile_commands.json>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    main_entry = None
    for e in data:
        f = e.get("file", "").replace("\\", "/")
        if f.endswith("/main/main.c"):
            main_entry = e
            break
    if not main_entry:
        return 0

    data = [e for e in data if Path(e.get("file", "")).name not in ("audio_mcp.c", "mcp_http.c")]

    directory = main_entry["directory"]
    cmd0 = main_entry["command"]

    for name in ("audio_mcp.c", "mcp_http.c"):
        cmd = cmd0.replace("main.c.obj", f"{name}.obj")
        cmd = cmd.replace("/main/main.c", f"/main/{name}")
        cmd = cmd.replace("\\main\\main.c", f"\\main\\{name}")
        cmd = augment_command(cmd, name)
        src = str((Path(directory).resolve().parent / "main" / name).resolve())
        data.append(
            {
                "directory": directory,
                "command": cmd,
                "file": src,
                "output": f"esp-idf/main/CMakeFiles/__idf_main.dir/{name}.obj",
            }
        )

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
