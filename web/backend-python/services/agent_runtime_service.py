import logging
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class AgentRuntimeService:
    """Agent 本地进程管理服务。"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.repo_root = Path(__file__).resolve().parents[3]
        self.agents_root = self.repo_root / "agents"

    def _is_starrocks(self) -> bool:
        return getattr(self.db, "db_type", "mysql") == "starrocks"

    def _next_id(self, table_name: str) -> int:
        row = self.db.execute_query(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table_name}")
        return int(row[0]["max_id"]) + 1 if row else 1

    def _runtime_key(self, agent_code: str, field: str) -> str:
        return f"agent_runtime.{agent_code}.{field}"

    def _ensure_within_repo(self, path_obj: Path) -> Path:
        resolved = path_obj.resolve()
        try:
            resolved.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"路径必须位于项目目录内: {resolved}") from exc
        return resolved

    def _upsert_system_config_entry(
        self,
        config_key: str,
        config_value: Any,
        config_type: str = "string",
        category: str = "agent",
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> None:
        update_sql = """
            UPDATE system_config
            SET config_value = %s, config_type = %s, category = %s,
                description = %s, is_active = %s, updated_at = NOW()
            WHERE config_key = %s
        """
        affected = self.db.execute_update(
            update_sql,
            (str(config_value), config_type, category, description, bool(is_active), config_key),
        )
        if affected > 0:
            return

        if self._is_starrocks():
            insert_sql = """
                INSERT INTO system_config
                (id, config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            self.db.execute_update(
                insert_sql,
                (
                    self._next_id("system_config"),
                    config_key,
                    str(config_value),
                    config_type,
                    category,
                    description,
                    bool(is_active),
                ),
            )
            return

        insert_sql = """
            INSERT INTO system_config
            (config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        self.db.execute_update(
            insert_sql,
            (config_key, str(config_value), config_type, category, description, bool(is_active)),
        )

    def _load_runtime_values(self, agent_code: str) -> Dict[str, Any]:
        sql = """
            SELECT config_key, config_value
            FROM system_config
            WHERE config_key LIKE %s AND is_active = TRUE
        """
        rows = self.db.execute_query(sql, (f"agent_runtime.{agent_code}.%",))
        result: Dict[str, Any] = {}
        prefix = f"agent_runtime.{agent_code}."
        for row in rows:
            key = str(row.get("config_key") or "")
            if not key.startswith(prefix):
                continue
            field = key.removeprefix(prefix)
            result[field] = row.get("config_value")
        return result

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    def _lookup_agent(self, agent_code: str) -> Optional[Dict[str, Any]]:
        rows = self.db.execute_query(
            """
            SELECT id, agent_code, agent_name, host, port, is_enabled
            FROM agent_config
            WHERE agent_code = %s
            LIMIT 1
            """,
            (agent_code,),
        )
        return rows[0] if rows else None

    @staticmethod
    def _probe_host(host: str) -> str:
        normalized = (host or "").strip().lower()
        if normalized in {"", "0.0.0.0", "localhost", "::"}:
            return "127.0.0.1"
        return host

    @staticmethod
    def resolve_local_ipv4() -> str:
        """本机局域网 IPv4（优先默认路由网卡，避免仅显示 127.0.0.1）。"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            pass
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
                addr = info[4][0]
                if addr and not addr.startswith("127."):
                    return addr
        except OSError:
            pass
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            pass
        return "127.0.0.1"

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    @classmethod
    def _wait_for_process_exit(cls, pid: int, timeout_seconds: float) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not cls._is_pid_running(pid):
                return True
            time.sleep(0.2)
        return not cls._is_pid_running(pid)

    @classmethod
    def _wait_for_port_ready(cls, host: str, port: int, timeout_seconds: float = 8.0) -> bool:
        target_host = cls._probe_host(host)
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with socket.create_connection((target_host, int(port)), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.25)
        return False

    def _resolve_launch_command(self, agent_code: str, host: str, port: int) -> tuple[list[str], Path]:
        runtime = self._load_runtime_values(agent_code)
        configured_command = str(runtime.get("command") or "").strip()
        configured_cwd = str(runtime.get("cwd") or "").strip()

        if configured_command:
            command = shlex.split(configured_command, posix=os.name != "nt")
            if not command:
                raise ValueError("runtime_command 不能为空")

            exe_name = Path(command[0]).name.lower()
            if exe_name in {"uv", "uv.exe"}:
                if len(command) < 2 or command[1] != "run":
                    raise ValueError("仅支持 `uv run ...` 启动命令")
            elif exe_name in {"python", "python.exe", "python3", "py", "py.exe"}:
                if len(command) < 2 or command[1].startswith("-"):
                    raise ValueError("仅支持 `python <script.py> ...` 启动命令")
            else:
                raise ValueError("runtime_command 仅允许 uv/python 启动方式")

            if "--host" not in command:
                command.extend(["--host", host])
            if "--port" not in command:
                command.extend(["--port", str(port)])

            cwd = Path(configured_cwd).expanduser() if configured_cwd else self.repo_root
            if not cwd.is_absolute():
                cwd = (self.repo_root / cwd).resolve()
            cwd = self._ensure_within_repo(cwd)
            if not cwd.exists():
                raise ValueError(f"Agent 启动目录不存在: {cwd}")

            if exe_name in {"python", "python.exe", "python3", "py", "py.exe"}:
                script_path = Path(command[1]).expanduser()
                if not script_path.is_absolute():
                    script_path = (cwd / script_path).resolve()
                script_path = self._ensure_within_repo(script_path)
                if not script_path.exists():
                    raise ValueError(f"Python 启动脚本不存在: {script_path}")
                command[1] = str(script_path)
            return command, cwd

        default_cwd = self._ensure_within_repo(self.agents_root / f"{agent_code}_agent")
        if not default_cwd.exists():
            raise ValueError(f"未找到Agent目录，请先配置 runtime_cwd: {default_cwd}")

        uv_bin = shutil.which("uv")
        if uv_bin and (default_cwd / "pyproject.toml").exists():
            return [uv_bin, "run", ".", "--host", host, "--port", str(port)], default_cwd

        main_script = default_cwd / "__main__.py"
        if main_script.exists():
            return [sys.executable, str(main_script), "--host", host, "--port", str(port)], default_cwd

        raise ValueError(f"无法推断Agent启动命令，请为 {agent_code} 配置 runtime_command")

    def get_runtime(self, agent_code: str) -> Dict[str, Any]:
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")

        agent = self._lookup_agent(normalized)
        if not agent:
            raise ValueError(f"未找到Agent: {normalized}")

        runtime = self._load_runtime_values(normalized)
        pid = self._to_int(runtime.get("pid"))
        is_running = bool(pid and self._is_pid_running(pid))
        status = str(runtime.get("status") or "").strip().lower()
        if not status:
            status = "running" if is_running else "stopped"
        elif status == "running" and not is_running:
            status = "stopped"

        host = str(runtime.get("host") or agent.get("host") or "127.0.0.1").strip()
        port = self._to_int(runtime.get("port")) or int(agent.get("port") or 0)
        server_ip = str(runtime.get("server_ip") or self.resolve_local_ipv4()).strip()

        return {
            "agent_code": normalized,
            "agent_name": agent.get("agent_name"),
            "status": status,
            "pid": pid if is_running else None,
            "host": host,
            "port": port,
            "server_ip": server_ip,
            "started_at": runtime.get("started_at"),
            "stopped_at": runtime.get("stopped_at"),
            "command": runtime.get("command"),
            "cwd": runtime.get("cwd"),
            "is_running": is_running,
        }

    def start_agent(self, agent_code: str) -> Dict[str, Any]:
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")

        agent = self._lookup_agent(normalized)
        if not agent:
            raise ValueError(f"未找到Agent: {normalized}")

        if not bool(agent.get("is_enabled", True)):
            raise ValueError("Agent 已在配置中禁用，请先在「Agent配置」中启用后再启动进程")

        current = self.get_runtime(normalized)
        if current["is_running"]:
            return current

        host = str(agent.get("host") or "127.0.0.1").strip()
        port = int(agent.get("port") or 0)
        if port <= 0:
            raise ValueError("Agent端口配置无效，无法启动")

        command, cwd = self._resolve_launch_command(normalized, host, port)
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")

        # 将数据挖掘Agent地址注入子Agent进程，使其可以独立查询用户偏好
        try:
            dm_rows = self.db.execute_query(
                "SELECT host, port FROM agent_config WHERE agent_code='data_mining' AND is_enabled=1 LIMIT 1"
            )
            if dm_rows:
                dm = dm_rows[0]
                dm_host = str(dm.get("host") or "localhost").strip()
                dm_port = str(dm.get("port") or "12003").strip()
                dm_url = dm_host if dm_host.startswith("http") else f"http://{dm_host}:{dm_port}"
                env["DATA_MINING_URL"] = dm_url
                logger.info("已向 %s 注入数据挖掘Agent地址: %s", normalized, dm_url)
        except Exception as exc:
            logger.warning("获取数据挖掘Agent地址失败（可选功能，子Agent将跳过偏好查询）: %s", exc)

        # 注入后端API地址，子Agent可调用接口录入设备操作记录（供数据挖掘使用）
        backend_host = os.environ.get("HOST", "localhost")
        backend_port = os.environ.get("PORT", "3000")
        if backend_host in ("0.0.0.0", ""):
            backend_host = "localhost"
        env.setdefault("BACKEND_URL", f"http://{backend_host}:{backend_port}")
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

        try:
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as exc:
            raise ValueError(f"启动Agent失败: {exc}") from exc

        time.sleep(0.7)
        if process.poll() is not None:
            raise ValueError(f"Agent启动失败，进程已退出，退出码: {process.returncode}")

        ready = self._wait_for_port_ready(host, port, timeout_seconds=8.0)
        status = "running" if ready else "starting"
        started_at = datetime.now(timezone.utc).isoformat()
        server_ip = self.resolve_local_ipv4()

        persist_items = {
            "status": status,
            "pid": str(process.pid),
            "host": host,
            "port": str(port),
            "server_ip": server_ip,
            "started_at": started_at,
            "stopped_at": "",
            "command": " ".join(command),
            "cwd": str(cwd),
        }
        for field, value in persist_items.items():
            self._upsert_system_config_entry(
                config_key=self._runtime_key(normalized, field),
                config_value=value,
                config_type="string",
                category="agent",
                description=f"{normalized} 运行时信息: {field}",
                is_active=True,
            )

        # 同步 host/port 到 agent_config（不修改 is_enabled，避免覆盖用户在界面上的禁用状态）
        self.db.execute_update(
            """
            UPDATE agent_config
            SET host = %s, port = %s, updated_at = NOW()
            WHERE agent_code = %s
            """,
            (host, port, normalized),
        )
        return self.get_runtime(normalized)

    def sync_runtimes_with_agent_config(self) -> Dict[str, Any]:
        """
        按 agent_config.is_enabled 对齐本地子进程：先停掉所有禁用，再启动所有启用。
        用于后端启动或与数据库配置漂移后的自愈。
        """
        rows = self.db.execute_query(
            "SELECT agent_code, is_enabled FROM agent_config ORDER BY id ASC"
        )
        stopped: List[str] = []
        started: List[str] = []
        errors: List[Dict[str, str]] = []

        disabled_codes: List[str] = []
        enabled_codes: List[str] = []
        for row in rows or []:
            code = str(row.get("agent_code") or "").strip()
            if not code:
                continue
            if bool(row.get("is_enabled")):
                enabled_codes.append(code)
            else:
                disabled_codes.append(code)

        for code in disabled_codes:
            try:
                self.stop_agent(code)
                stopped.append(code)
            except ValueError:
                pass
            except Exception as exc:
                logger.warning("同步停止 Agent 失败: %s, err=%s", code, exc)
                errors.append({"agent_code": code, "phase": "stop", "error": str(exc)})

        for code in enabled_codes:
            try:
                self.start_agent(code)
                started.append(code)
            except Exception as exc:
                logger.warning("同步启动 Agent 失败: %s, err=%s", code, exc)
                errors.append({"agent_code": code, "phase": "start", "error": str(exc)})

        return {"stopped": stopped, "started": started, "errors": errors}

    def stop_agent(self, agent_code: str) -> Dict[str, Any]:
        normalized = (agent_code or "").strip()
        if not normalized:
            raise ValueError("agent_code 不能为空")

        agent = self._lookup_agent(normalized)
        if not agent:
            raise ValueError(f"未找到Agent: {normalized}")

        current = self.get_runtime(normalized)
        pid = current.get("pid")

        if isinstance(pid, int) and self._is_pid_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception as exc:
                logger.warning("发送SIGTERM失败，agent=%s, pid=%s, err=%s", normalized, pid, exc)
            if not self._wait_for_process_exit(pid, timeout_seconds=4.0):
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception as exc:
                    logger.warning("发送SIGKILL失败，agent=%s, pid=%s, err=%s", normalized, pid, exc)

        stopped_at = datetime.now(timezone.utc).isoformat()
        persist_items = {
            "status": "stopped",
            "pid": "",
            "stopped_at": stopped_at,
        }
        for field, value in persist_items.items():
            self._upsert_system_config_entry(
                config_key=self._runtime_key(normalized, field),
                config_value=value,
                config_type="string",
                category="agent",
                description=f"{normalized} 运行时信息: {field}",
                is_active=True,
            )
        return self.get_runtime(normalized)
