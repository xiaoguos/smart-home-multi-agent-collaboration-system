from collections.abc import AsyncIterable
from typing import Any, Dict
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from database_config import get_db_config

from tools import (
    get_scene_recommendations,
    analyze_user_patterns,
    get_device_preferences,
    predict_next_action
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


class DataMiningAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    SYSTEM_PROMPT = (
        '你是一个专业的用户行为数据挖掘助手，专注于分析智能家居设备的使用习惯。'
        '你的主要职责是：'
        '1. **场景识别**：理解用户的自然语言描述，准确识别用户当前的场景'
        '   - "我要睡觉了"、"准备睡觉" → 识别为"睡觉"场景'
        '   - "起床了"、"早上好" → 识别为"起床"场景'
        '   - "我出门了"、"要出去了" → 识别为"离家"场景'
        '   - "到家了"、"回来了" → 识别为"回家"场景'
        '   - "开始工作"、"要办公了" → 识别为"工作"场景'
        ''
        '2. **习惯挖掘**：基于StarRocks数据库中的历史数据，挖掘用户的设备使用习惯'
        '   - 分析用户在特定场景下的设备操作模式'
        '   - 识别常用的设备设置参数（如空调温度、灯光亮度等）'
        '   - 发现时间相关的使用规律'
        ''
        '3. **智能建议**：为中央agent提供个性化的设备控制建议'
        '   - 基于历史数据给出置信度高的建议'
        '   - 如果没有足够的历史数据，明确告知，让中央agent使用其他方式（如MCP搜索）获取建议'
        '   - 建议要具体，包含设备类型、操作和参数'
        ''
        '工具使用指南：'
        '1. **get_scene_recommendations**：当用户描述一个场景时（如"我睡觉了"），使用此工具'
        '   - 首先识别场景类型（睡觉、起床、离家、回家、工作等）'
        '   - 从数据库挖掘该场景的历史操作习惯'
        '   - 返回具体的设备控制建议'
        ''
        '2. **analyze_user_patterns**：分析用户的整体使用模式'
        '   - 识别最常用的设备'
        '   - 发现使用时间规律'
        '   - 提供统计分析'
        ''
        '3. **get_device_preferences**：获取用户对特定设备的偏好'
        '   - 分析用户对某个设备的常用设置'
        '   - 如：空调的常用温度、灯光的常用亮度'
        ''
        '4. **predict_next_action**：基于当前时间预测用户可能的操作'
        '   - 根据历史数据预测用户接下来可能的设备操作'
        ''
        '重要原则：'
        '- 如果数据库中没有足够的历史数据（样本数<3），明确告知"暂无足够历史数据"'
        '- 所有建议都要包含置信度和样本数量'
        '- 建议格式要清晰，便于中央agent理解和执行'
        '- 始终用中文回复，语言要专业但易懂'
    )

    FORMAT_INSTRUCTION = (
        '如果用户需要提供更多信息来完成请求，请将响应状态设置为 input_required。'
        '如果在处理请求时出现错误，请将响应状态设置为 error。'
        '如果请求已完成，请将响应状态设置为 completed。'
    )
    
    def __init__(self):
        # 初始化数据库
        self.db_config = get_db_config()
        logger.info(f"数据挖掘Agent使用数据库类型: {self.db_config.db_type}")
        
        # 测试数据库连接
        if self.db_config.test_connection():
            logger.info("数据库连接成功")
        else:
            logger.warning("数据库连接失败，将使用备用方案")
        
        self.model = ChatOpenAI(
            model='deepseek-chat',
            openai_api_key='sk-0f603ccc4af94854ac560c59f223b1d5',
            openai_api_base='https://api.deepseek.com',
            temperature=0,
        )
        
        self.tools = [
            get_scene_recommendations,
            analyze_user_patterns,
            get_device_preferences,
            predict_next_action
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
                if any(name == 'get_scene_recommendations' for name in tool_names):
                    tip = '正在识别场景并挖掘历史使用习惯…'
                elif any(name == 'analyze_user_patterns' for name in tool_names):
                    tip = '正在分析用户设备使用模式…'
                elif any(name == 'get_device_preferences' for name in tool_names):
                    tip = '正在查询设备偏好设置…'
                elif any(name == 'predict_next_action' for name in tool_names):
                    tip = '正在预测用户可能的操作…'
                else:
                    tip = '正在挖掘数据…'
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': tip,
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '数据挖掘完成，正在整理分析结果…',
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

