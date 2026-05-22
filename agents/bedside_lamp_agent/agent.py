from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

import dotenv
import logging
import os
from pathlib import Path

dotenv.load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

from tools import (
    get_lamp_status,
    set_lamp_power,
    set_lamp_brightness,
    set_lamp_color_temp,
    set_lamp_color,
    set_lamp_scene,
    query_user_lamp_preferences,
    record_device_operation,
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_ai_config_from_env() -> dict:
    """从环境变量读取 AI 模型配置，缺少必填项时抛出异常。"""
    model = os.environ.get("AI_MODEL", "").strip()
    api_key = os.environ.get("AI_API_KEY", "").strip()
    api_base = os.environ.get("AI_API_BASE", "").strip()
    temperature = float(os.environ.get("AI_TEMPERATURE", "0.7"))

    missing = [k for k, v in [("AI_MODEL", model), ("AI_API_KEY", api_key), ("AI_API_BASE", api_base)] if not v]
    if missing:
        raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}，请在 .env 中配置。")

    return {"model": model, "api_key": api_key, "api_base": api_base, "temperature": temperature}


class BedsideLampAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    DEFAULT_SYSTEM_PROMPT = (
        '你是一个专门的Yeelink床头灯控制助手（型号：yeelink.light.bslamp2）。'
        '你的唯一目的是帮助用户控制他们的床头灯。'
        '你可以帮助：开关灯、调节亮度、设置色温、改变颜色、应用预设场景等。'
        '如果用户询问与床头灯控制无关的内容，'
        '请礼貌地说明你无法帮助处理该主题，只能协助处理与床头灯相关的问题。'
        '不要尝试回答无关问题或将工具用于其他目的。'
        '\n\n## 个性化偏好查询（重要）'
        '当用户以场景或意图描述需求（如"睡觉了"、"准备睡觉"、"要阅读"、"起床"、"浪漫一点"），'
        '且未明确给出亮度/色温具体数值时，必须先调用 query_user_lamp_preferences(scene=场景描述) '
        '获取该用户的历史习惯偏好，再按偏好结果设置参数。'
        '若数据挖掘返回 available=false 或无历史数据，则使用下方默认参数。'
        '\n\n## 工具使用指南'
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
        '6. 场景模式（无历史偏好时的默认值）：'
        '   - "阅读模式/看书"：使用 set_lamp_scene(scene="reading") - 100%亮度，4000K中性光'
        '   - "睡眠模式/睡觉"：使用 set_lamp_scene(scene="sleep") - 10%亮度，2000K暖光'
        '   - "浪漫模式/约会"：使用 set_lamp_scene(scene="romantic") - 30%亮度，粉红色'
        '   - "夜灯模式/起夜"：使用 set_lamp_scene(scene="night") - 5%亮度，1700K极暖光'
        ''
        '始终用友好、简洁的中文回复用户，告知用户是按其历史习惯还是默认参数执行的。'
        '\n\n## 操作记录（重要）'
        '每次成功执行设备控制后（开关、调光、调色温、设置颜色、切换场景），'
        '必须调用 record_device_operation 工具将本次操作记录到数据库，'
        '参数包括：action（操作名）、parameters（参数字典）、success=true、response（结果描述）。'
        '此记录是系统学习用户习惯的数据来源，不可省略。'
        '若设备操作失败，也应以 success=false 和 error_message 记录失败原因。'
    )

    def __init__(self):
        self._model_signature: tuple[str, str, str, float] | None = None
        self._prompt_signature: str | None = None

        self.tools = [
            get_lamp_status,
            set_lamp_power,
            set_lamp_brightness,
            set_lamp_color_temp,
            set_lamp_color,
            set_lamp_scene,
            query_user_lamp_preferences,
            record_device_operation,
        ]

        self._refresh_runtime_config(force=True)

    def _build_system_prompt(self) -> str:
        custom = os.environ.get("AGENT_SYSTEM_PROMPT", "").strip()
        return custom if custom else self.DEFAULT_SYSTEM_PROMPT

    def _refresh_runtime_config(self, force: bool = False) -> None:
        ai_config = _get_ai_config_from_env()
        model_signature = (
            str(ai_config['model']),
            str(ai_config['api_key']),
            str(ai_config['api_base']),
            float(ai_config['temperature']),
        )
        prompt = self._build_system_prompt()

        if (
            not force
            and self._model_signature == model_signature
            and self._prompt_signature == prompt
        ):
            return

        self.model = ChatOpenAI(
            model=ai_config['model'],
            api_key=ai_config['api_key'],
            base_url=ai_config['api_base'],
            temperature=ai_config['temperature'],
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
        logger.info("♻️ Bedside Lamp Agent 已应用最新模型配置: %s", ai_config['model'])

    async def invoke(self, query, context_id) -> dict[str, Any]:
        """非流式调用，直接返回最终结果"""
        try:
            self._refresh_runtime_config()
        except Exception as e:
            logger.warning("动态刷新 Bedside Lamp 模型配置失败，继续使用当前配置: %s", e)

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

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        messages = current_state.values.get('messages') if hasattr(current_state, 'values') else None

        if not isinstance(messages, list) or not messages:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': '当前无法处理您的请求，请稍后重试。',
            }

        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                text = self._extract_text_from_message(msg)
                if text:
                    return {
                        'is_task_complete': True,
                        'require_user_input': False,
                        'content': text,
                    }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': '当前无法处理您的请求，请稍后重试。',
        }
