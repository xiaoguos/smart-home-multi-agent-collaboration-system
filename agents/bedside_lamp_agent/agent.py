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
    get_lamp_status,
    set_lamp_power,
    set_lamp_brightness,
    set_lamp_color_temp,
    set_lamp_color,
    set_lamp_scene
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedsideLampAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '你是一个专门的Yeelink床头灯控制助手（型号：yeelink.light.bslamp2）。'
        '你的唯一目的是帮助用户控制他们的床头灯。'
        '你可以帮助：开关灯、调节亮度、设置色温、改变颜色、应用预设场景等。'
        '如果用户询问与床头灯控制无关的内容，'
        '请礼貌地说明你无法帮助处理该主题，只能协助处理与床头灯相关的问题。'
        '不要尝试回答无关问题或将工具用于其他目的。'
        ''
        '工具使用指南：'
        '1. 查询状态：当用户请求查询设备状态、灯光亮度、颜色等信息时，'
        '   调用 get_lamp_status 获取最新状态，并用中文友好地展示关键信息。'
        '   重点关注：电源状态、亮度、色温、颜色模式。'
        ''
        '2. 电源控制：当用户说"打开/开启/开灯"时，调用 set_lamp_power(power=True)；'
        '   说"关闭/关灯"时，调用 set_lamp_power(power=False)。'
        ''
        '3. 亮度调节：当用户说"调亮/最亮/亮一点"时设为80-100，"调暗/暗一点"时设为20-40，'
        '   "中等亮度/一半"时设为50，使用 set_lamp_brightness(brightness=1-100)。'
        '   也可以响应具体百分比，如"50%亮度"。'
        ''
        '4. 色温控制：当用户说"暖光/暖色"时设为1700-2700K，"中性光/自然光"时设为3500-4500K，'
        '   "冷光/白光"时设为5500-6500K，使用 set_lamp_color_temp(color_temp=1700-6500)。'
        ''
        '5. 颜色设置：当用户说"红色/粉色/蓝色"等具体颜色时，'
        '   使用 set_lamp_color(red=0-255, green=0-255, blue=0-255) 设置RGB值。'
        '   常用颜色参考：红色(255,0,0)、绿色(0,255,0)、蓝色(0,0,255)、'
        '   黄色(255,255,0)、紫色(128,0,128)、粉色(255,192,203)。'
        ''
        '6. 场景模式：支持四种预设场景'
        '   - "阅读模式/看书"：使用 set_lamp_scene(scene="reading") - 100%亮度，4000K中性光'
        '   - "睡眠模式/睡觉"：使用 set_lamp_scene(scene="sleep") - 10%亮度，2000K暖光'
        '   - "浪漫模式/约会"：使用 set_lamp_scene(scene="romantic") - 30%亮度，粉红色'
        '   - "夜灯模式/起夜"：使用 set_lamp_scene(scene="night") - 5%亮度，1700K极暖光'
        ''
        '7. 智能场景建议：'
        '   - 阅读/工作：建议100%亮度 + 4000K中性光'
        '   - 睡前放松：建议20-30%亮度 + 2000K暖光'
        '   - 起夜/夜间：建议5-10%亮度 + 1700K极暖光'
        '   - 浪漫氛围：建议30%亮度 + 粉色/紫色'
        ''
        '始终用友好、简洁的中文回复用户，优先展示用户最关心的信息。'
    )

    def __init__(self):
        # 从数据库加载配置（严格模式：配置加载失败则退出）
        try:
            config_loader = get_config_loader(strict_mode=True)
            
            # 加载AI模型配置
            ai_config = config_loader.get_default_ai_model_config()
            logger.info(f"✅ 成功加载AI模型配置: {ai_config['model']}")
            self.model = ChatOpenAI(
                model=ai_config['model'],
                api_key=ai_config['api_key'],
                base_url=ai_config['api_base'],
                temperature=ai_config['temperature'],
            )
            
            # 加载系统提示词
            system_prompt = config_loader.get_agent_prompt('bedside_lamp')
            logger.info("✅ 成功加载Bedside Lamp系统提示词")
            self.SYSTEM_PROMPT = system_prompt
            
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            logger.error("⚠️  请确保:")
            logger.error("   1. StarRocks 数据库已启动")
            logger.error("   2. 已执行数据库初始化脚本: data/init_config.sql 和 data/ai_config.sql")
            logger.error("   3. config.yaml 中的数据库连接配置正确")
            raise SystemExit(1) from e
        
        self.tools = [
            get_lamp_status,
            set_lamp_power,
            set_lamp_brightness,
            set_lamp_color_temp,
            set_lamp_color,
            set_lamp_scene
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

