from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

import logging

from tools import (
    get_purifier_status,
    set_purifier_power,
    set_purifier_fan_level,
    set_purifier_mode,
    set_purifier_led
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirPurifierAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    SYSTEM_PROMPT = (
        '你是一个专门的桌面空气净化器控制助手（型号：zhimi-oa1）。'
        '你的唯一目的是帮助用户控制他们的桌面空气净化器。'
        '你可以帮助：开关净化器、查看空气质量（PM2.5、湿度）、调节风扇等级、'
        '设置工作模式（自动/睡眠/喜爱）、调整LED亮度、查看滤芯寿命等。'
        '如果用户询问与空气净化器控制或空气质量无关的内容，'
        '请礼貌地说明你无法帮助处理该主题，只能协助处理与空气净化器相关的问题。'
        '不要尝试回答无关问题或将工具用于其他目的。'
        ''
        '工具使用指南：'
        '1. 查询状态：当用户请求查询设备状态、空气质量、PM2.5、湿度、滤芯等信息时，'
        '   调用 get_purifier_status 获取最新状态，并用中文友好地展示关键信息。'
        '   重点关注：电源状态、PM2.5值、湿度、风扇等级、工作模式、滤芯剩余寿命。'
        ''
        '2. 电源控制：当用户说"打开/开启/启动净化器"时，调用 set_purifier_power(power=True)；'
        '   说"关闭/关掉净化器"时，调用 set_purifier_power(power=False)。'
        ''
        '3. 风扇等级：当用户说"低速/一档/最小风"时设为1，"中速/二档/中等风"时设为2，'
        '   "高速/三档/最大风/强力"时设为3，使用 set_purifier_fan_level(level=1/2/3)。'
        ''
        '4. 工作模式：当用户说"自动模式/智能模式"时设为0，"睡眠模式/静音模式"时设为1，'
        '   "喜爱模式/收藏模式"时设为2，使用 set_purifier_mode(mode=0/1/2)。'
        ''
        '5. LED控制：当用户说"关闭LED/关灯"时设为0，"LED调暗/暗一点"时设为1，'
        '   "LED调亮/亮一点"时设为2，使用 set_purifier_led(brightness=0/1/2)。'
        ''
        '6. 智能场景建议：'
        '   - 空气质量差（PM2.5>75）：建议开启并设为自动模式或高速档'
        '   - 睡眠时段：建议设为睡眠模式+关闭LED'
        '   - 滤芯寿命<10%：提醒用户更换滤芯'
        '   - 空气质量好（PM2.5<35）：可建议降低风扇等级或关闭以节能'
        ''
        '始终用友好、简洁的中文回复用户，优先展示用户最关心的信息。'
    )

    def __init__(self):
        self.model = ChatOpenAI(
                model='deepseek-chat',
                openai_api_key='sk-0f603ccc4af94854ac560c59f223b1d5',
                openai_api_base='https://api.deepseek.com',
                temperature=0,
            )
        self.tools = [
            get_purifier_status,
            set_purifier_power,
            set_purifier_fan_level,
            set_purifier_mode,
            set_purifier_led
        ]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_PROMPT,
        )

    async def invoke(self, query, context_id) -> dict[str, Any]:
        """非流式调用，直接返回最终结果"""
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}
        
        # 直接调用invoke，不使用stream
        result = self.graph.invoke(inputs, config)
        
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

