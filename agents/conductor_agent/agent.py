from collections.abc import AsyncIterable
from typing import Any, Literal
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

import logging

from tools import (
    list_available_agents,
    execute_agent_command,
    get_agent_status,
    control_device,
    get_system_overview,
    analyze_user_behavior,
    get_user_insights,
    query_data_mining_agent,
    get_xiaomi_devices
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseFormat(BaseModel):
    message: str

class ConductorAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    SYSTEM_PROMPT = (
        '你是一个智能家居总管理助手，负责协调和管理所有智能设备代理。'
        '你的主要职责包括：'
        '1. 管理多个智能设备代理（如空调代理、空气净化器代理等）'
        '2. 协调不同代理之间的工作'
        '3. 提供统一的智能家居控制接口'
        '4. 监控系统整体状态'
        '5. 管理小米智能设备信息查询'
        ''
        '你可以执行以下操作：'
        '- 列出所有可用的代理服务：使用 list_available_agents 工具'
        '- 检查代理状态：使用 get_agent_status 工具'
        '- 向特定代理发送命令：使用 execute_agent_command 工具（适用于复杂的代理间通信）'
        '- 控制智能设备：使用 control_device 工具（推荐用于设备控制，会自动调用对应代理并记录日志）'
        '- 获取系统概览：使用 get_system_overview 工具'
        '- 分析用户行为：使用 analyze_user_behavior 工具'
        '- 获取用户洞察：使用 get_user_insights 工具'
        '- **场景智能分析**：使用 query_data_mining_agent 工具（重要！）'
        ''
        '小米设备信息管理：'
        '- 获取小米设备信息：使用 get_xiaomi_devices 工具'
        '  需要提供：username（小米账号）、password（密码）、server（服务器区域，默认cn）'
        '  返回：所有小米设备的详细信息，包括Token、IP、MAC等'
        ''
        '设备控制指南：'
        '当用户说"开启空调"、"打开空调"、"关闭空调"等命令时，使用 control_device 工具：'
        '  - device_type: "air_conditioner" （空调）'
        '  - action: "开启空调" 或 "关闭空调" 或其他用户说的操作'
        '  - parameters: 如果有额外参数（如温度），以字典形式传递'
        ''
        '当用户说"开启空气净化器"、"关闭空气净化器"等命令时，使用 control_device 工具：'
        '  - device_type: "air_cleaner" （空气净化器）'
        '  - action: 对应的操作'
        ''
        '当用户询问系统状态时，优先调用 get_system_overview 获取整体概览。'
        '当用户询问可用服务时，使用 list_available_agents 工具。'
        '当用户询问使用习惯或需要个性化建议时，使用 analyze_user_behavior 或 get_user_insights 工具。'
        ''
        '**场景智能分析（核心功能）**：'
        '当用户描述一个生活场景时（例如："我要睡觉了"、"起床了"、"要出门了"、"到家了"），'
        '必须优先使用 query_data_mining_agent 工具：'
        '1. 数据挖掘代理会自动识别用户描述的场景类型'
        '2. 从StarRocks数据库挖掘该场景下的历史使用习惯'
        '3. 提供个性化的设备控制建议（如空调温度、床头灯亮度等）'
        '4. 如果数据挖掘代理返回"暂无足够历史数据"，则可以使用默认设置或提示用户'
        ''
        '场景处理流程示例：'
        '用户说："我要睡觉了" → '
        '  1. 调用 query_data_mining_agent，传入"我要睡觉了"'
        '  2. 数据挖掘代理识别为"睡觉"场景'
        '  3. 返回建议：关闭主灯、打开床头灯(亮度10%)、开启空调(25°C)、净化器睡眠模式'
        '  4. 根据建议依次调用 control_device 执行设备控制'
        ''
        '始终以中文回复用户，提供清晰、友好的服务。'
        '如果用户的需求超出了你的能力范围，请礼貌地说明并提供相关建议。'
    )

    FORMAT_INSTRUCTION = (
        '如果用户需要提供更多信息来完成请求，请将响应状态设置为 input_required。'
        '如果在处理请求时出现错误，请将响应状态设置为 error。'
        '如果请求已完成，请将响应状态设置为 completed。'
    )
    
    def __init__(self):
        self.model = ChatOpenAI(
                model='deepseek-chat',
                openai_api_key='sk-0f603ccc4af94854ac560c59f223b1d5',
                openai_api_base='https://api.deepseek.com',
                temperature=0,
            )
        self.tools = [
            list_available_agents,
            execute_agent_command,
            get_agent_status,
            control_device,
            get_system_overview,
            analyze_user_behavior,
            get_user_insights,
            query_data_mining_agent,
            get_xiaomi_devices
        ]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_PROMPT,
        )

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                tool_names = [tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', '') for tc in message.tool_calls]
                if any(name == 'list_available_agents' for name in tool_names):
                    tip = '正在获取可用代理列表…'
                elif any(name == 'get_agent_status' for name in tool_names):
                    tip = '正在检查代理状态…'
                elif any(name == 'execute_agent_command' for name in tool_names):
                    tip = '正在向代理发送命令…'
                elif any(name == 'control_device' for name in tool_names):
                    tip = '正在控制智能设备…'
                elif any(name == 'get_system_overview' for name in tool_names):
                    tip = '正在获取系统概览…'
                elif any(name == 'analyze_user_behavior' for name in tool_names):
                    tip = '正在分析用户行为数据…'
                elif any(name == 'get_user_insights' for name in tool_names):
                    tip = '正在生成用户洞察…'
                elif any(name == 'query_data_mining_agent' for name in tool_names):
                    tip = '正在分析场景并挖掘使用习惯…'
                elif any(name == 'get_xiaomi_devices' for name in tool_names):
                    tip = '正在获取小米设备信息…'
                else:
                    tip = '正在处理您的请求…'
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': tip,
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '已获取系统数据，正在整理结果…',
                }

        yield self.get_agent_response(config)

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

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        messages = current_state.values.get('messages') if hasattr(current_state, 'values') else None

        # 优先返回最近一次工具消息内容
        if isinstance(messages, list) and messages:
            for msg in reversed(messages):
                if isinstance(msg, ToolMessage):
                    tool_text = self._extract_text_from_message(msg)
                    if tool_text:
                        return {
                            'is_task_complete': True,
                            'require_user_input': False,
                            'content': tool_text,
                        }

        # 回退到最后一条 AI 消息
        final_text = ''
        if isinstance(messages, list) and messages:
            last_msg = messages[-1]
            final_text = self._extract_text_from_message(last_msg)

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

