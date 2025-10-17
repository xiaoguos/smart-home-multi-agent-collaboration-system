from collections.abc import AsyncIterable
from typing import Any, Literal
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

import logging

from tools import (
    save_device_operation_log,
    analyze_user_habits,
    get_user_operation_history,
    predict_user_preference,
    get_system_analytics
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseFormat(BaseModel):
    message: str

class DataMiningAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    SYSTEM_PROMPT = (
        '你是一个专业的数据挖掘和分析助手，专门负责分析智能家居用户的使用习惯和行为模式。'
        '你的主要职责包括：'
        '1. 分析用户设备操作历史，挖掘使用习惯和偏好'
        '2. 预测用户可能的设备设置偏好'
        '3. 提供个性化的设备控制建议'
        '4. 生成系统使用统计和分析报告'
        '5. 保存和管理用户操作日志'
        ''
        '你可以执行以下操作：'
        '- 保存设备操作日志：使用 save_device_operation_log 工具'
        '- 分析用户习惯：使用 analyze_user_habits 工具'
        '- 获取操作历史：使用 get_user_operation_history 工具'
        '- 预测用户偏好：使用 predict_user_preference 工具'
        '- 获取系统分析：使用 get_system_analytics 工具'
        ''
        '当用户询问使用习惯时，优先调用 analyze_user_habits 进行深度分析。'
        '当需要预测用户偏好时，使用 predict_user_preference 工具。'
        '当需要查看操作历史时，使用 get_user_operation_history 工具。'
        '当需要系统整体分析时，使用 get_system_analytics 工具。'
        ''
        '始终以中文回复用户，提供详细的数据分析结果和洞察。'
        '分析结果应该包含具体的数字、趋势和可操作的建议。'
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
            save_device_operation_log,
            analyze_user_habits,
            get_user_operation_history,
            predict_user_preference,
            get_system_analytics
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
                if any(name == 'save_device_operation_log' for name in tool_names):
                    tip = '正在保存设备操作日志…'
                elif any(name == 'analyze_user_habits' for name in tool_names):
                    tip = '正在分析用户使用习惯…'
                elif any(name == 'get_user_operation_history' for name in tool_names):
                    tip = '正在获取用户操作历史…'
                elif any(name == 'predict_user_preference' for name in tool_names):
                    tip = '正在预测用户偏好…'
                elif any(name == 'get_system_analytics' for name in tool_names):
                    tip = '正在生成系统分析报告…'
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
                    'content': '已获取分析数据，正在整理结果…',
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

