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

from tools import (
    get_purifier_status,
    set_purifier_power,
    set_purifier_mode,
    set_purifier_fan_level,
    set_purifier_led,
    set_purifier_alarm,
    set_purifier_child_lock
)
from skills_catalog import format_skills_for_llm, user_message_skill_prefix

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirPurifierAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '你是一个专门的桌面空气净化器控制助手（型号：zhimi-oa1）。'
        '你的唯一目的是帮助用户控制他们的桌面空气净化器。'
        '你可以帮助：开关净化器、查看空气质量（PM2.5、湿度）、调节风扇等级（1-4档）、'
        '控制LED按键亮度、提示音开关、童锁、查看滤芯寿命等。'
        '如果用户询问与空气净化器控制或空气质量无关的内容，'
        '请礼貌地说明你无法帮助处理该主题，只能协助处理与空气净化器相关的问题。'
        '不要尝试回答无关问题或将工具用于其他目的。'
        ''
        '工具使用指南：'
        '1. 查询状态：当用户请求查询设备状态、空气质量、PM2.5、湿度、滤芯等信息时，'
        '   调用 get_purifier_status 获取最新状态，并用中文友好地展示关键信息。'
        '   重点关注：电源状态、PM2.5值、湿度、风扇等级、滤芯剩余寿命。'
        ''
        '2. 电源控制：当用户说"打开/开启/启动净化器"时，调用 set_purifier_power(power=True)；'
        '   说"关闭/关掉净化器"时，调用 set_purifier_power(power=False)。'
        ''
        '3. 工作模式：支持0=自动模式（根据PM2.5自动调节）、1=睡眠模式（低噪音）、2=手动模式（手动设置风扇等级）。'
        '   使用 set_purifier_mode(mode=0/1/2) 设置。注意：要手动设置风扇等级，设备必须先切换到手动模式（mode=2）。'
        ''
        '4. 风扇等级：支持1-4档，当用户说"一档/最小风"时设为1，"二档"时设为2，'
        '   "三档"时设为3，"四档/最大风/强力"时设为4，使用 set_purifier_fan_level(level=1/2/3/4)。'
        '   **重要**：set_purifier_fan_level 工具会自动检查并切换到手动模式，无需手动调用 set_purifier_mode。'
        ''
        '5. LED控制：当用户说"开启LED/开灯"时设为True，"关闭LED/关灯"时设为False，'
        '   使用 set_purifier_led(brightness=True/False)。'
        ''
        '6. 提示音控制：当用户说"开启提示音/打开声音"时设为True，"关闭提示音/静音"时设为False，'
        '   使用 set_purifier_alarm(alarm=True/False)。'
        ''
        '7. 童锁控制：当用户说"开启童锁/锁定按键"时设为True，"关闭童锁/解锁按键"时设为False，'
        '   使用 set_purifier_child_lock(child_lock=True/False)。'
        ''
        '8. 智能场景建议：'
        '   - 空气质量差（PM2.5>75）：建议开启并设为高速档（4档）或自动模式'
        '   - 睡眠时段：建议设为睡眠模式（mode=1）或低速档（1档）+关闭LED+关闭提示音'
        '   - 滤芯寿命<10%：提醒用户更换滤芯'
        '   - 空气质量好（PM2.5<35）：可建议降低风扇等级、切换到自动模式或关闭以节能'
        ''
        '始终用友好、简洁的中文回复用户，优先展示用户最关心的信息。'
    )

    def __init__(self):
        # 从数据库加载配置（严格模式：配置加载失败则退出）
        try:
            config_loader = get_config_loader(strict_mode=True)
            
            # 加载AI模型配置
            ai_config = config_loader.get_default_ai_model_config()
            self.model = ChatOpenAI(
                model=ai_config['model'],
                api_key=ai_config['api_key'],
                base_url=ai_config['api_base'],
                temperature=ai_config['temperature'],
            )
            
            # 加载系统提示词，并附加 A2A Skills 说明供模型对齐 skill id 与工具
            system_prompt = config_loader.get_agent_prompt('air_cleaner')
            base = system_prompt if system_prompt else self.DEFAULT_SYSTEM_PROMPT
            self.SYSTEM_PROMPT = base + "\n\n" + format_skills_for_llm()
            
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            logger.error("⚠️  请确保:")
            logger.error("   1. StarRocks 数据库已启动")
            logger.error("   2. 已执行数据库初始化脚本: data/init_config.sql 和 data/ai_config.sql")
            logger.error("   3. config.yaml 中的数据库连接配置正确")
            raise SystemExit(1) from e
        
        self.tools = [
            get_purifier_status,
            set_purifier_power,
            set_purifier_mode,
            set_purifier_fan_level,
            set_purifier_led,
            set_purifier_alarm,
            set_purifier_child_lock
        ]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_PROMPT,
        )

    async def invoke(
        self,
        query: str,
        context_id: str,
        skill_id: str | None = None,
    ) -> dict[str, Any]:
        """非流式调用，直接返回最终结果。skill_id 来自 A2A 请求 metadata，用于强调当前技能上下文。"""
        user_text = user_message_skill_prefix(skill_id) + query
        inputs = {'messages': [('user', user_text)]}
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

