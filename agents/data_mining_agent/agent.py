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
    query_user_scene_habits,
    get_data_mining_status,
    submit_user_feedback
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataMiningAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '你是一个专业的用户行为数据挖掘助手，负责分析智能家居系统中的用户使用习惯。'
        '你的主要职责是：'
        '1. 从StarRocks数据库中读取用户的设备操作历史'
        '2. 使用高斯混合模型(GMM)对用户行为进行场景聚类分析'
        '3. 识别用户的使用模式和习惯'
        '4. 为Conductor Agent提供个性化的场景推荐'
        ''
        '工具使用指南：'
        '1. 场景习惯查询：当需要分析用户在特定场景下的习惯时，'
        '   调用 query_user_scene_habits 工具，传入用户查询（如"睡觉"、"起床"、"回家"）'
        '   该工具会：'
        '   - 从数据库读取用户最近N天的设备操作记录'
        '   - 使用GMM算法进行场景聚类'
        '   - 分析每个场景的设备操作特征'
        '   - 匹配与用户查询最相关的场景'
        '   - 返回该场景的设备操作建议'
        ''
        '2. 状态查询：当需要了解数据挖掘Agent的运行状态时，'
        '   调用 get_data_mining_status 工具获取系统状态和统计信息'
        ''
        '数据分析流程：'
        '第一步：特征提取'
        '  - 从操作时间提取：小时、分钟、星期几、是否周末、时段特征'
        '  - 从设备类型提取：设备类别编码'
        ''
        '第二步：GMM聚类'
        '  - 使用高斯混合模型对特征进行聚类'
        '  - 自动确定最优聚类数量（2-5个场景）'
        '  - 每个聚类代表一个用户使用场景'
        ''
        '第三步：场景分析'
        '  - 分析每个场景的时间特征（早上/下午/晚上/夜晚）'
        '  - 统计每个场景中的设备操作频次'
        '  - 提取最常见的操作和参数'
        ''
        '第四步：场景匹配'
        '  - 根据用户查询中的关键词匹配场景'
        '  - 考虑时间特征和设备类型'
        '  - 返回最相关场景的操作建议'
        ''
        '数据不足处理：'
        '当历史数据不足时（少于10条记录），明确告知调用方：'
        '  - 返回 status: "insufficient_data"'
        '  - 建议使用通用最佳实践'
        '  - Conductor Agent会启用保底方案（AI搜索）'
        ''
        '响应格式：'
        '始终返回JSON格式的分析结果，包含：'
        '  - status: 状态（success/insufficient_data/error）'
        '  - message: 描述信息'
        '  - matched_scene: 匹配的场景信息'
        '  - recommendation: 具体的设备操作建议'
        '  - all_scenes: 所有识别的场景列表'
        ''
        '与Conductor Agent的协作：'
        '你是Conductor Agent的数据支持服务，专注于：'
        '  - 提供基于历史数据的个性化建议'
        '  - 识别用户的使用习惯和偏好'
        '  - 当数据不足时，及时告知以便启用备选方案'
        ''
        '始终以中文回复，提供清晰、结构化的分析结果。'
    )

    def __init__(self):
        # 从数据库加载配置（严格模式：配置加载失败则退出）
        try:
            self.config_loader = get_config_loader(strict_mode=True)
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            logger.error("⚠️  请确保:")
            logger.error("   1. StarRocks 数据库已启动")
            logger.error("   2. 已执行数据库初始化脚本: data/init_config.sql 和 data/ai_config.sql")
            logger.error("   3. .env 或 config.yaml 中的数据库连接配置正确")
            raise SystemExit(1) from e
        
        self._model_signature: tuple[str, str, str, float] | None = None
        self._prompt_signature: str | None = None

        self.tools = [
            query_user_scene_habits,
            get_data_mining_status,
            submit_user_feedback
        ]

        # 启动时初始化一次；后续每次 invoke 前会按数据库配置热更新
        self._refresh_runtime_config(force=True)

    def _build_system_prompt(self) -> str:
        try:
            system_prompt = self.config_loader.get_agent_prompt('data_mining')
        except Exception:
            system_prompt = None
        if system_prompt:
            return system_prompt
        logger.warning("⚠️ 未找到数据挖掘Agent的系统提示词，使用默认提示词")
        return self.DEFAULT_SYSTEM_PROMPT

    def _refresh_runtime_config(self, force: bool = False) -> None:
        ai_config = self.config_loader.get_ai_model_config_for_agent("data_mining")
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
        logger.info("♻️ Data Mining Agent 已应用最新模型配置: %s", ai_config['model'])

    async def invoke(self, query, context_id) -> dict[str, Any]:
        """非流式调用，直接返回最终结果"""
        try:
            self._refresh_runtime_config()
        except Exception as e:
            logger.warning("动态刷新 Data Mining 模型配置失败，继续使用当前配置: %s", e)

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

        # 优先返回最近一次AI消息内容（包含工具调用结果）
        if isinstance(messages, list) and messages:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    ai_text = self._extract_text_from_message(msg)
                    if ai_text:
                        return {
                            'is_task_complete': True,
                            'require_user_input': False,
                            'content': ai_text,
                        }

        # 回退到最后一条消息
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

