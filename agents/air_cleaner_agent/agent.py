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


class AirPurifierAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    DEFAULT_SYSTEM_PROMPT = (
        "你是一个桌面空气净化器控制助手。"
        "你只能处理空气净化器相关请求，例如状态查询、电源、模式、风扇、LED、提示音和童锁。"
        "如果用户问题与空气净化器无关，请礼貌拒绝并引导回相关操作。"
    )

    def __init__(self):
        self._model_signature: tuple[str, str, str, float] | None = None
        self._prompt_signature: str | None = None

        self.tools = [
            get_purifier_status,
            set_purifier_power,
            set_purifier_mode,
            set_purifier_fan_level,
            set_purifier_led,
            set_purifier_alarm,
            set_purifier_child_lock
        ]

        self._refresh_runtime_config(force=True)

    def _build_system_prompt(self) -> str:
        return self.DEFAULT_SYSTEM_PROMPT + "\n\n" + format_skills_for_llm()

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
        logger.info("♻️ Air Cleaner Agent 已应用最新模型配置: %s", ai_config['model'])

    async def invoke(
        self,
        query: str,
        context_id: str,
        skill_id: str | None = None,
    ) -> dict[str, Any]:
        """非流式调用，直接返回最终结果。skill_id 来自 A2A 请求 metadata，用于强调当前技能上下文。"""
        try:
            self._refresh_runtime_config()
        except Exception as e:
            logger.warning("动态刷新 Air Cleaner 模型配置失败，继续使用当前配置: %s", e)

        user_text = user_message_skill_prefix(skill_id) + query
        inputs = {'messages': [('user', user_text)]}
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

        final_text = ''
        if isinstance(messages, list) and messages:
            final_text = self._extract_text_from_message(messages[-1])

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
