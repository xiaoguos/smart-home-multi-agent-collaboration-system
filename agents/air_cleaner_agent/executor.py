import logging

from a2a.helpers import (
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Message,
    UnsupportedOperationError,
)

from agent import AirPurifierAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AirPurifierAgentExecutor(AgentExecutor):
    """Air Purifier AgentExecutor."""

    def __init__(self):
        self.agent = AirPurifierAgent()

    @staticmethod
    def _extract_skill_id_from_context(context: RequestContext) -> str | None:
        """从 MessageSendParams 或 Message 的 metadata 读取 A2A skillId。"""
        keys = ("skillId", "skill_id", "a2a.skillId")
        meta = context.metadata
        for k in keys:
            if k in meta and meta[k]:
                return str(meta[k])
        msg: Message | None = context.message
        if msg and msg.metadata:
            m = msg.metadata
            for k in keys:
                if k in m and m[k]:
                    return str(m[k])
        return None

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise InvalidParamsError()

        query = context.get_user_input()
        task = context.current_task
        if not task:
            if context.message is None:
                raise InvalidParamsError(message="缺少用户消息")
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        if context.task_id is None or context.context_id is None:
            raise InternalError(message="任务上下文缺失")

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            skill_id = self._extract_skill_id_from_context(context)
            # 使用非流式invoke方法（传入 A2A skillId 以便模型对齐技能）
            result = await self.agent.invoke(query, task.context_id, skill_id=skill_id)
            
            is_task_complete = result.get('is_task_complete', True)
            require_user_input = result.get('require_user_input', False)
            content = result.get('content', '处理完成')
            
            if require_user_input:
                await updater.requires_input(
                    message=updater.new_agent_message(
                        parts=[new_text_part(content)],
                    )
                )
            elif is_task_complete:
                await updater.add_artifact(
                    [new_text_part(content)],
                    name='purifier_status_result',
                )
                await updater.complete()
            else:
                # 如果既不需要输入也未完成，设置为working状态
                await updater.start_work(
                    message=updater.new_agent_message(
                        parts=[new_text_part(content)],
                    )
                )

        except (InvalidParamsError, InternalError, UnsupportedOperationError):
            raise
        except Exception as e:
            logger.error(f'An error occurred while processing the request: {e}')
            raise InternalError(message=str(e)) from e

    def _validate_request(self, context: RequestContext) -> bool:
        # 这里可以添加请求验证逻辑
        # 返回 True 表示有错误，False 表示验证通过
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise UnsupportedOperationError()

