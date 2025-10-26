from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

import logging
import sys
import os

# 添加父目录到路径以导入config_loader
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import get_config_loader

from tools import get_ac_status, set_ac_power, set_ac_temperature

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirConditionerAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '你是一个专门的家庭空调控制助手。'
        '你的唯一目的是帮助用户控制他们的家庭空调系统。'
        '你可以帮助调节温度、设置模式（制冷、制热、送风等）、'
        '打开或关闭空调，以及提供节能建议。'
        '如果用户询问与空调控制或相关主题无关的内容，'
        '请礼貌地说明你无法帮助处理该主题，只能协助处理与空调相关的问题。'
        '不要尝试回答无关问题或将工具用于其他目的。'
        '当用户请求查询设备状态时，一定要调用工具 get_ac_status 获取最新状态，并将结果直接返回给用户；如工具返回 JSON，请原样返回或提取关键字段用中文概述。'
        '当用户请求"启动/打开/关闭空调"等同义表达时，必须调用 set_ac_power(power: bool) 工具执行，并向用户反馈执行结果。'
        '当用户请求设置温度（如"调到26度/设置到23℃"）时，必须调用 set_ac_temperature(temperature: int) 工具执行；如用户未给出明确温度，先向用户确认目标温度（范围16-30℃）。'
        '当用户以语义描述温感（如"有点热/太热/冷一点/暖一点/舒服点/睡觉用"）而未给出具体温度时，按以下规则自动设置人类适宜温度：'
        '1) 先调用 get_ac_status 获取当前 power、mode、tar_temp；若电源关闭且需要调温，先调用 set_ac_power(true)。'
        '2) 若 mode 为 制冷/自动 且用户表达"有点热/太热/降温/冷一点"，将目标温度在当前基础上降低1-2℃（默认2℃），不低于24℃；若表达"有点冷/太冷/升温/暖一点"，则提高1-2℃（默认2℃），不高于30℃，然后调用 set_ac_temperature。'
        '3) 若 mode 为 制热 且用户表达"有点冷/太冷/升温/暖一点"，在当前基础上提高1-2℃（默认2℃），不高于26℃；若表达"有点热/太热/降温/冷一点"，则降低1-2℃（默认2℃），不低于16℃，然后调用 set_ac_temperature。'
        '4) 若用户表达"舒适/舒服点"，则：制冷模式设为26℃，制热模式设为22℃；若无法判断模式，则先查询状态后按模式执行。'
        '5) 若用户表达"睡觉/睡眠"，则：制冷模式设为27℃，制热模式设为21℃。'
        '所有自动推断出的目标温度都必须限制在16-30℃区间内。设置完成后，用中文简要说明采用了哪条规则与最终温度。'
    )

    def __init__(self):
        # 从数据库加载配置
        config_loader = get_config_loader()
        
        # 加载AI模型配置
        ai_config = config_loader.get_default_ai_model_config()
        if ai_config:
            logger.info(f"从数据库加载AI模型配置: {ai_config['model']}")
            self.model = ChatOpenAI(
                model=ai_config['model'],
                openai_api_key=ai_config['api_key'],
                openai_api_base=ai_config['api_base'],
                temperature=ai_config['temperature'],
            )
        else:
            logger.warning("使用默认AI模型配置")
            self.model = ChatOpenAI(
                model='deepseek-chat',
                openai_api_key='sk-0f603ccc4af94854ac560c59f223b1d5',
                openai_api_base='https://api.deepseek.com',
                temperature=0,
            )
        
        # 加载系统提示词
        system_prompt = config_loader.get_agent_prompt('air_conditioner')
        if system_prompt:
            logger.info("从数据库加载Air Conditioner系统提示词")
            self.SYSTEM_PROMPT = system_prompt
        else:
            logger.warning("使用默认系统提示词")
            self.SYSTEM_PROMPT = self.DEFAULT_SYSTEM_PROMPT
        
        self.tools = [get_ac_status,set_ac_power,set_ac_temperature]

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

