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

from tools import get_ac_status, set_ac_power, set_ac_temperature

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


class AirConditionerAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '你是一个专门的家庭智能设备管理助手。'
        '你的主要功能包括：1）控制空调系统；2）查询和管理用户的米家智能设备。'
        '\n\n## 设备查询功能'
        '当用户询问"我有哪些设备"、"列出设备"、"设备列表"等问题时，必须调用 list_devices 工具获取所有米家设备信息。'
        '**重要**: 调用 list_devices 时必须传入 system_user_id 参数，当前用户为 admin，系统ID为 1000000001。'
        '该工具会自动从数据库读取用户的米家账户凭证，无需用户输入账号密码。'
        '如果工具返回"未查询到绑定米家账户的Token"，请友好地告知用户需要先绑定米家账户。'
        '如果工具返回"请先开启设备查询MCP"，请告知用户MCP服务未启动。'
        '\n\n## 空调控制功能'
        '你可以帮助调节温度、设置模式（制冷、制热、送风等）、打开或关闭空调，以及提供节能建议。'
        '当用户请求查询设备状态时，一定要调用工具 get_ac_status 获取最新状态，并将结果直接返回给用户；如工具返回 JSON，请原样返回或提取关键字段用中文概述。'
        '当用户请求"启动/打开/关闭空调"等同义表达时，必须调用 set_ac_power(power: bool) 工具执行，并向用户反馈执行结果。'
        '当用户请求设置温度（如"调到26度/设置到23℃"）时，必须调用 set_ac_temperature(temperature: int) 工具执行；如用户未给出明确温度，先向用户确认目标温度（范围16-30℃）。'
        '\n\n## 智能温度调节'
        '当用户以语义描述温感（如"有点热/太热/冷一点/暖一点/舒服点/睡觉用"）而未给出具体温度时，按以下规则自动设置人类适宜温度：'
        '1) 先调用 get_ac_status 获取当前 power、mode、tar_temp；若电源关闭且需要调温，先调用 set_ac_power(true)。'
        '2) 若 mode 为 制冷/自动 且用户表达"有点热/太热/降温/冷一点"，将目标温度在当前基础上降低1-2℃（默认2℃），不低于24℃；若表达"有点冷/太冷/升温/暖一点"，则提高1-2℃（默认2℃），不高于30℃，然后调用 set_ac_temperature。'
        '3) 若 mode 为 制热 且用户表达"有点冷/太冷/升温/暖一点"，在当前基础上提高1-2℃（默认2℃），不高于26℃；若表达"有点热/太热/降温/冷一点"，则降低1-2℃（默认2℃），不低于16℃，然后调用 set_ac_temperature。'
        '4) 若用户表达"舒适/舒服点"，则：制冷模式设为26℃，制热模式设为22℃；若无法判断模式，则先查询状态后按模式执行。'
        '5) 若用户表达"睡觉/睡眠"，则：制冷模式设为27℃，制热模式设为21℃。'
        '所有自动推断出的目标温度都必须限制在16-30℃区间内。设置完成后，用中文简要说明采用了哪条规则与最终温度。'
        '\n\n如果用户询问与智能设备管理或空调控制无关的内容，请礼貌地说明你只能协助处理智能设备相关的问题。'
    )

    def __init__(self):
        self._model_signature: tuple[str, str, str, float] | None = None
        self._prompt_signature: str | None = None

        from tools import list_devices
        self.tools = [get_ac_status, set_ac_power, set_ac_temperature, list_devices]

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
        logger.info("♻️ Air Conditioner Agent 已应用最新模型配置: %s", ai_config['model'])

    async def invoke(self, query, context_id) -> dict[str, Any]:
        """非流式调用，直接返回最终结果"""
        try:
            self._refresh_runtime_config()
        except Exception as e:
            logger.warning("动态刷新 Air Conditioner 模型配置失败，继续使用当前配置: %s", e)

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

