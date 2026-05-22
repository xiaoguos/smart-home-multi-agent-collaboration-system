from typing import Any, Dict, FrozenSet, List, Set
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

import asyncio
import logging
import time

from conductor.config_loader import get_config_loader
from conductor.tools import (
    list_available_agents,
    execute_agent_command,
    get_agent_status,
    control_device,
    get_system_overview,
    analyze_user_behavior,
    get_user_insights,
    query_data_mining_agent,
    list_xiaomi_devices,
    search_baidu_ai,
)
from conductor.dida_tools import (
    manage_dida_task,
    manage_dida_project,
)
from conductor.wechat_tools import (
    get_wechat_chat_history,
    send_wechat_message,
    send_multiple_wechat_messages,
    send_wechat_to_multiple_friends,
)
from conductor.windows_tools import (
    manage_windows_app,
    execute_powershell_command,
    execute_windows_shortcut,
)
from conductor.esp32_audio_tools import (
    list_esp32_audio_mcp_tools,
    invoke_esp32_audio_mcp_tool,
)
from conductor.rag_tool import query_knowledge_base

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 不依赖账户级插件开关的基础能力（Windows 本地能力视为核心）
_CORE_TOOL_NAMES: FrozenSet[str] = frozenset(
    {
        "list_available_agents",
        "execute_agent_command",
        "get_agent_status",
        "control_device",
        "get_system_overview",
        "analyze_user_behavior",
        "get_user_insights",
        "query_data_mining_agent",
        "query_knowledge_base",
        "search_baidu_ai",
        "manage_windows_app",
        "execute_powershell_command",
        "execute_windows_shortcut",
    }
)

# 插件 key -> 工具名（须与 @tool 名称一致；与后端 PLUGIN_MODE_KEYS 对齐）
_PLUGIN_TO_TOOL_NAMES: Dict[str, FrozenSet[str]] = {
    "xiaomi": frozenset({"list_xiaomi_devices"}),
    "dida": frozenset({"manage_dida_task", "manage_dida_project"}),
    "wechat": frozenset(
        {
            "get_wechat_chat_history",
            "send_wechat_message",
            "send_multiple_wechat_messages",
            "send_wechat_to_multiple_friends",
        }
    ),
    "audio": frozenset({"list_esp32_audio_mcp_tools", "invoke_esp32_audio_mcp_tool"}),
}


class ConductorAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '''你是一个智能家居总管理助手，同时也是一个友好的AI助手。

## ⚠️ 重要：何时使用工具 vs 直接回答

**知识库查询原则（强制执行）**：
**每次回答用户问题之前，都必须先调用 query_knowledge_base 检索一次**，无论问题类型。
- 若检索到相关内容，将其作为回答依据
- 若检索结果为空，再根据通用知识或其他工具回答
- 唯一例外：纯粹的闲聊打招呼（如"你好"、"谢谢"）可跳过检索

**需要调用其他工具的情况**（在 RAG 检索之后再决定是否调用）：
- 用户明确要求控制设备（如"打开空调"、"关闭灯"）
- 查询设备状态（如"空调温度是多少"）
- 查询设备列表（如"我有哪些设备"）
- 分析使用习惯（如"我通常什么时候开空调"）
- 场景设置（如"我要睡觉了"、"起床了"）

你的主要职责包括：
1. 管理多个智能设备代理（如空调代理、空气净化器代理等）
2. 协调不同代理之间的工作
3. 提供统一的智能家居控制接口
4. 监控系统整体状态
5. 管理小米智能设备信息查询
6. 回答用户的一般性问题

你可以执行以下操作：
- 列出所有可用的代理服务：使用 list_available_agents 工具
- 检查代理状态：使用 get_agent_status 工具
- 向特定代理发送命令：使用 execute_agent_command 工具（适用于复杂的代理间通信）
- 控制智能设备：使用 control_device 工具（推荐用于设备控制，会自动调用对应代理并记录日志）
- 获取系统概览：使用 get_system_overview 工具
- 分析用户行为：使用 analyze_user_behavior 工具
- 获取用户洞察：使用 get_user_insights 工具
- **场景智能分析**：使用 query_data_mining_agent 工具（重要！）

## 知识库查询（强制）
用户可能已将个人日程、习惯偏好、操作规则、设备说明等存入知识库。
**每次回答前都必须先调用 query_knowledge_base**，以知识库结果为优先依据。
- 知识库有内容 → 基于内容回答
- 知识库无内容 → 根据通用知识或其他工具回答，并告知用户可将相关信息存入知识库

## 米家与其它插件能力
若下方系统提示中列出了「插件：米家 / 滴答 / 微信」等段落，表明当前已启用对应能力；请严格按段落说明选用工具。
未列出的插件即未对当前 Agent 开放，不要调用相关工具名。
当用户询问「我有哪些设备 / 米家设备」且已启用米家插件时，使用 list_xiaomi_devices，**system_user_id 必传**（与当前登录用户一致），勿索要米家密码。

设备控制指南：
当用户说"开启空调"、"打开空调"、"关闭空调"等命令时，使用 control_device 工具：
  - device_type: "air_conditioner" （空调）
  - action: "开启空调" 或 "关闭空调" 或其他用户说的操作
  - parameters: 如果有额外参数（如温度），以字典形式传递

当用户说"开启空气净化器"、"关闭空气净化器"等命令时，使用 control_device 工具：
  - device_type: "air_cleaner" （空气净化器）
  - action: 对应的操作

**⚠️ 重要：工具返回值处理**
- control_device 工具返回的是 JSON 格式，包含 success、message、content、operation_record 等字段
- **你必须解析这个 JSON，提取 content 或 message 字段中的文本，然后用自然语言回复用户**
- **绝对不要直接返回 JSON 字符串给用户！**
- 示例：
  - 工具返回：{"success": true, "message": "已打开空调", "content": "空调已开启，温度设置为24度"}
  - 你应该回复："好的，我已经为您打开空调，温度设置为24度。"

当用户询问系统状态时，优先调用 get_system_overview 获取整体概览。
当用户询问可用服务时，使用 list_available_agents 工具。
当用户询问使用习惯或需要个性化建议时，使用 analyze_user_behavior 或 get_user_insights 工具。

**场景智能分析（核心功能）**：
当用户描述一个生活场景时（例如："我要睡觉了"、"起床了"、"要出门了"、"到家了"），
或用户指令模糊时（例如："打开空调"但未指定温度），使用以下智能处理流程：

**智能处理流程（两级保底机制）**：
第一步：优先使用历史习惯数据
  1. 调用 query_data_mining_agent 工具，传入用户场景或指令
  2. 数据挖掘代理会从StarRocks数据库挖掘用户历史使用习惯
  3. 如果有足够的历史数据，返回个性化建议（如"您通常在睡觉时将空调设为26°C"）
  4. 根据个性化建议执行设备控制

第二步：保底方案 - AI搜索通用最佳实践
  当数据挖掘代理返回以下情况时，启用保底方案：
  - 返回"暂无足够历史数据"
  - 返回"同一时间操作记录过少"
  - 用户是新用户，没有历史记录
  - 历史数据不足以提供有价值的建议
  
  启用保底方案步骤：
  1. 调用 search_baidu_ai 工具
  2. 传入智能查询，如："人类最适合的睡觉温度"、"睡觉时最适合的灯光设置"
  3. 获取基于人体工程学和通用最佳实践的建议
  4. 向用户说明："根据通用最佳实践，建议...（随着您使用次数增多，我会学习您的个人习惯）"
  5. 根据通用建议执行设备控制

始终以中文回复用户，提供清晰、友好的服务。
如果用户的需求超出了你的能力范围，请礼貌地说明并提供相关建议。
消息返回请使用Markdown格式。'''
    )

    def __init__(self):
        # 从数据库加载配置（严格模式：配置加载失败则退出）
        try:
            self.config_loader = get_config_loader(strict_mode=True)
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            logger.error("⚠️  请确保:")
            logger.error("   1. StarRocks 数据库已启动")
            logger.error("   2. 已执行数据库初始化脚本: data/init_config.sql 和 data/ai_config.sql")
            logger.error("   3. .env 或 config.yaml 中的数据库连接配置正确")
            raise SystemExit(1) from e

        self._model_signature: tuple[str, str, str, float] | None = None
        self._prompt_signature: str | None = None
        self._plugin_signature: tuple[str, ...] | None = None
        self._tool_names_signature: tuple[str, ...] | None = None
        # 上次热更新检查的时间戳，避免每次请求都打 DB
        self._last_refresh_ts: float = 0.0
        # 热更新检查间隔（秒）
        self._refresh_interval: float = 30.0

        self.tools: List[Any] = []

        # 启动时初始化一次；后续每次 invoke 前会按数据库配置热更新
        self._refresh_runtime_config(force=True)

    def _collect_conductor_tools(self) -> List[Any]:
        """按 Agent 插件配置与 config.yaml 裁剪 LangChain 工具列表。"""
        eff = self.config_loader.get_effective_agent_plugin_keys("conductor")
        eff_set: Set[str] = set(eff)
        allowed: Set[str] = set(_CORE_TOOL_NAMES)
        for pk in eff:
            allowed |= set(_PLUGIN_TO_TOOL_NAMES.get(pk, frozenset()))

        ordered = [
            list_available_agents,
            execute_agent_command,
            get_agent_status,
            control_device,
            get_system_overview,
            analyze_user_behavior,
            get_user_insights,
            query_data_mining_agent,
            query_knowledge_base,
            list_xiaomi_devices,
            search_baidu_ai,
            manage_dida_task,
            manage_dida_project,
            get_wechat_chat_history,
            send_wechat_message,
            send_multiple_wechat_messages,
            send_wechat_to_multiple_friends,
            manage_windows_app,
            execute_powershell_command,
            execute_windows_shortcut,
            list_esp32_audio_mcp_tools,
            invoke_esp32_audio_mcp_tool,
        ]

        out: List[Any] = []
        for t in ordered:
            name = getattr(t, "name", None) or ""
            if name not in allowed:
                continue
            if name in ("list_esp32_audio_mcp_tools", "invoke_esp32_audio_mcp_tool"):
                if "audio" not in eff_set:
                    continue
                if not self.config_loader.get_esp32_audio_mcp_config().get("enabled"):
                    continue
            out.append(t)
        return out

    def _build_system_prompt(self) -> str:
        try:
            system_prompt = self.config_loader.get_agent_prompt("conductor")
        except Exception:
            system_prompt = None
        prompt = system_prompt if system_prompt else self.DEFAULT_SYSTEM_PROMPT

        eff = self.config_loader.get_effective_agent_plugin_keys("conductor")
        esp32_cfg = self.config_loader.get_esp32_audio_mcp_config()
        audio_first = ""
        if "audio" in eff and bool(esp32_cfg.get("enabled")):
            audio_first = (
                "## 音频输出优先（ESP32 / Arduino MCP）\n"
                "在「账户 → 插件扩展」中为音频/ESP32 配置并启用 MCP（或沿用 config.yaml 的 esp32_audio_mcp）时，"
                "凡涉及录音、播放、串口音频及硬件音频输入输出，**必须优先**使用 list_esp32_audio_mcp_tools 与 "
                "invoke_esp32_audio_mcp_tool 完成；先列出工具名再调用，arguments_json 为 JSON 对象字符串（无参可用 \"{}\"）。"
                "勿用其他途径替代，除非用户明确要求。\n\n"
            )
        prompt = audio_first + (prompt or "")

        addon = self.config_loader.build_agent_plugin_prompt_addon("conductor")
        if addon:
            prompt = (prompt or "").rstrip() + "\n\n" + addon
        return prompt

    def _refresh_runtime_config(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_refresh_ts) < self._refresh_interval:
            return
        self._last_refresh_ts = now

        ai_config = self.config_loader.get_ai_model_config_for_agent("conductor")
        model_signature = (
            str(ai_config["model"]),
            str(ai_config["api_key"]),
            str(ai_config["api_base"]),
            float(ai_config["temperature"]),
        )
        prompt = self._build_system_prompt()
        new_tools = self._collect_conductor_tools()
        plugin_signature = tuple(sorted(self.config_loader.get_effective_agent_plugin_keys("conductor")))
        tool_names_sig = tuple(sorted(getattr(t, "name", "") for t in new_tools))

        if (
            not force
            and self._model_signature == model_signature
            and self._prompt_signature == prompt
            and self._plugin_signature == plugin_signature
            and self._tool_names_signature == tool_names_sig
        ):
            return

        self.tools = new_tools

        self.model = ChatOpenAI(
            model=ai_config["model"],
            api_key=ai_config["api_key"],
            base_url=ai_config["api_base"],
            temperature=ai_config["temperature"],
        )
        self.SYSTEM_PROMPT = prompt
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_PROMPT,
        )
        self._model_signature = model_signature
        self._prompt_signature = prompt
        self._plugin_signature = plugin_signature
        self._tool_names_signature = tool_names_sig
        logger.info(
            "♻️ Conductor Agent 已刷新：模型=%s 插件=%s 工具数=%s",
            ai_config["model"],
            ",".join(plugin_signature) or "(仅核心)",
            len(self.tools),
        )

    async def invoke(self, query, context_id) -> dict[str, Any]:
        """非流式调用，直接返回最终结果"""
        try:
            await asyncio.to_thread(self._refresh_runtime_config)
        except Exception as e:
            logger.warning("动态刷新 Conductor 模型配置失败，继续使用当前配置: %s", e)

        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        await self.graph.ainvoke(inputs, config)

        return self.get_agent_response(config)

    def _extract_text_from_message(self, msg: AIMessage | ToolMessage | Any) -> str:
        try:
            content = getattr(msg, 'content', None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and 'text' in part:
                        parts.append(part['text'])
                if parts:
                    return '\n'.join(parts)
        except Exception:
            pass
        return ''

    def _parse_tool_output(self, tool_text: str) -> str:
        """
        解析工具输出，提取用户友好的消息
        
        如果工具返回 JSON 格式（如 control_device），提取 content 或 message 字段
        否则直接返回原文本
        """
        try:
            import json
            # 尝试解析为 JSON
            data = json.loads(tool_text)
            
            # 如果是我们的标准工具返回格式
            if isinstance(data, dict):
                # 优先返回 content 字段（通常是最友好的消息）
                if 'content' in data and data['content']:
                    return data['content']
                # 其次返回 message 字段
                if 'message' in data and data['message']:
                    return data['message']
                # 如果有推荐信息（数据挖掘Agent）
                if 'recommendation' in data:
                    # 返回原 JSON，让 Agent 自己格式化
                    return tool_text
        except (json.JSONDecodeError, ValueError):
            # 不是 JSON 格式，直接返回
            pass
        
        return tool_text

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        messages = current_state.values.get('messages') if hasattr(current_state, 'values') else None

        # 优先返回最后一条 AI 消息（Agent 的总结）
        final_text = ''
        if isinstance(messages, list) and messages:
            last_msg = messages[-1]
            final_text = self._extract_text_from_message(last_msg)
            
            # 如果最后一条是 AI 消息且有内容，直接返回
            if isinstance(last_msg, AIMessage) and final_text:
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': final_text,
                }

        # 如果没有 AI 总结消息，回退到工具消息
        if isinstance(messages, list) and messages:
            for msg in reversed(messages):
                if isinstance(msg, ToolMessage):
                    tool_text = self._extract_text_from_message(msg)
                    if tool_text:
                        # 解析工具输出，提取用户友好的内容
                        parsed_content = self._parse_tool_output(tool_text)
                        return {
                            'is_task_complete': True,
                            'require_user_input': False,
                            'content': parsed_content,
                        }

        if not final_text:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': '当前无法处理您的请求，请稍后重试。',
            }

        return {
            'is_task_complete': True,
            'require_user_input': False,
            'content': final_text,
        }

