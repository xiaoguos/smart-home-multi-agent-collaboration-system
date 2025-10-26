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
    list_available_agents,
    execute_agent_command,
    get_agent_status,
    control_device,
    get_system_overview,
    analyze_user_behavior,
    get_user_insights,
    query_data_mining_agent,
    get_xiaomi_devices,
    search_baidu_ai
)

memory = MemorySaver()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConductorAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    # 默认系统提示词（备用）
    DEFAULT_SYSTEM_PROMPT = (
        '你是一个智能家居总管理助手，负责协调和管理所有智能设备代理。'
        '你的主要职责包括：'
        '1. 管理多个智能设备代理（如空调代理、空气净化器代理等）'
        '2. 协调不同代理之间的工作'
        '3. 提供统一的智能家居控制接口'
        '4. 监控系统整体状态'
        '5. 管理小米智能设备信息查询'
        ''
        '你可以执行以下操作：'
        '- 列出所有可用的代理服务：使用 list_available_agents 工具'
        '- 检查代理状态：使用 get_agent_status 工具'
        '- 向特定代理发送命令：使用 execute_agent_command 工具（适用于复杂的代理间通信）'
        '- 控制智能设备：使用 control_device 工具（推荐用于设备控制，会自动调用对应代理并记录日志）'
        '- 获取系统概览：使用 get_system_overview 工具'
        '- 分析用户行为：使用 analyze_user_behavior 工具'
        '- 获取用户洞察：使用 get_user_insights 工具'
        '- **场景智能分析**：使用 query_data_mining_agent 工具（重要！）'
        ''
        '小米设备信息管理：'
        '- 获取小米设备信息：使用 get_xiaomi_devices 工具'
        '  需要提供：username（小米账号）、password（密码）、server（服务器区域，默认cn）'
        '  返回：所有小米设备的详细信息，包括Token、IP、MAC等'
        ''
        '设备控制指南：'
        '当用户说"开启空调"、"打开空调"、"关闭空调"等命令时，使用 control_device 工具：'
        '  - device_type: "air_conditioner" （空调）'
        '  - action: "开启空调" 或 "关闭空调" 或其他用户说的操作'
        '  - parameters: 如果有额外参数（如温度），以字典形式传递'
        ''
        '当用户说"开启空气净化器"、"关闭空气净化器"等命令时，使用 control_device 工具：'
        '  - device_type: "air_cleaner" （空气净化器）'
        '  - action: 对应的操作'
        ''
        '当用户询问系统状态时，优先调用 get_system_overview 获取整体概览。'
        '当用户询问可用服务时，使用 list_available_agents 工具。'
        '当用户询问使用习惯或需要个性化建议时，使用 analyze_user_behavior 或 get_user_insights 工具。'
        ''
        '**场景智能分析（核心功能）**：'
        '当用户描述一个生活场景时（例如："我要睡觉了"、"起床了"、"要出门了"、"到家了"），'
        '或用户指令模糊时（例如："打开空调"但未指定温度），使用以下智能处理流程：'
        ''
        '**智能处理流程（两级保底机制）**：'
        '第一步：优先使用历史习惯数据'
        '  1. 调用 query_data_mining_agent 工具，传入用户场景或指令'
        '  2. 数据挖掘代理会从StarRocks数据库挖掘用户历史使用习惯'
        '  3. 如果有足够的历史数据，返回个性化建议（如"您通常在睡觉时将空调设为26°C"）'
        '  4. 根据个性化建议执行设备控制'
        ''
        '第二步：保底方案 - AI搜索通用最佳实践'
        '  当数据挖掘代理返回以下情况时，启用保底方案：'
        '  - 返回"暂无足够历史数据"'
        '  - 返回"同一时间操作记录过少"'
        '  - 用户是新用户，没有历史记录'
        '  - 历史数据不足以提供有价值的建议'
        '  '
        '  启用保底方案步骤：'
        '  1. 调用 search_baidu_ai 工具'
        '  2. 传入智能查询，如："人类最适合的睡觉温度"、"睡觉时最适合的灯光设置"'
        '  3. 获取基于人体工程学和通用最佳实践的建议'
        '  4. 向用户说明："根据通用最佳实践，建议...（随着您使用次数增多，我会学习您的个人习惯）"'
        '  5. 根据通用建议执行设备控制'
        ''
        '**完整场景示例**：'
        '用户说："我要睡觉了" → '
        '  情况A（有历史数据）：'
        '    1. 调用 query_data_mining_agent("我要睡觉了")'
        '    2. 返回："根据您的历史习惯，睡觉时空调26°C、床头灯10%亮度"'
        '    3. 执行个性化设置'
        '  '
        '  情况B（无历史数据）：'
        '    1. 调用 query_data_mining_agent("我要睡觉了")'
        '    2. 返回："暂无足够历史数据"'
        '    3. 调用 search_baidu_ai("人类最适合的睡觉温度和灯光设置")'
        '    4. 返回："根据睡眠医学，建议26-28°C、极低亮度暖光"'
        '    5. 向用户说明这是通用建议，并执行设置'
        '    6. 提示："我会记住这次设置，下次为您提供更个性化的建议"'
        ''
        '始终以中文回复用户，提供清晰、友好的服务。'
        '如果用户的需求超出了你的能力范围，请礼貌地说明并提供相关建议。'
        '消息返回请使用Markdown'
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
        system_prompt = config_loader.get_agent_prompt('conductor')
        if system_prompt:
            logger.info("从数据库加载Conductor系统提示词")
            self.SYSTEM_PROMPT = system_prompt
        else:
            logger.warning("使用默认系统提示词")
            self.SYSTEM_PROMPT = self.DEFAULT_SYSTEM_PROMPT
        
        self.tools = [
            list_available_agents,
            execute_agent_command,
            get_agent_status,
            control_device,
            get_system_overview,
            analyze_user_behavior,
            get_user_insights,
            query_data_mining_agent,
            get_xiaomi_devices,
            search_baidu_ai  # 百度AI搜索保底方案
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

