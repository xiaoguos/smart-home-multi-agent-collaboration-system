"""
主入口点 - 用于 `uv run .` 或 `python -m conductor_agent` 启动服务
"""

import sys
from pathlib import Path

# 确保当前目录和父目录在 Python 路径中
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from main import main

if __name__ == "__main__":
    main()

