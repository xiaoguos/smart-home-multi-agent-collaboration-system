import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from agent import DataMiningAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataMiningAgentExecutor(AgentExecutor):
    """Data Mining AgentExecutor."""

    def __init__(self):
        self.agent = DataMiningAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)  # type: ignore
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            # 使用非流式invoke方法
            result = await self.agent.invoke(query, task.context_id)
            
            is_task_complete = result.get('is_task_complete', True)
            require_user_input = result.get('require_user_input', False)
            content = result.get('content', '处理完成')
            
            if require_user_input:
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(
                        content,
                        task.context_id,
                        task.id,
                    ),
                    final=True,
                )
            elif is_task_complete:
                await updater.add_artifact(
                    [Part(root=TextPart(text=content))],
                    name='data_mining_result',
                )
                await updater.complete()
            else:
                # 如果既不需要输入也未完成，设置为working状态
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        content,
                        task.context_id,
                        task.id,
                    ),
                )

        except Exception as e:
            logger.error(f'An error occurred while processing the request: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        # 这里可以添加请求验证逻辑
        # 返回 True 表示有错误，False 表示验证通过
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())

