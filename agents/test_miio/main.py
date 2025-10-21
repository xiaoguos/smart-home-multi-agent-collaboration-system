import logging
import asyncio
from uuid import uuid4
import httpx
from a2a.client import ClientFactory, A2ACardResolver
from a2a.types import Message, Part
from a2a.client.client import ClientConfig

async def main():
    logging.basicConfig(level=logging.INFO)

    base_url = 'http://localhost:12004'

    async with httpx.AsyncClient(timeout=30.0) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        print('成功获取代理卡')

        config = ClientConfig(
            streaming=True,
            polling=False,
            httpx_client=httpx_client,
            supported_transports=["JSONRPC","http_json"],
            use_client_preference=False,
            accepted_output_modes=["text", "text/plain"]
        )

        factory = ClientFactory(config=config)
        client = factory.create(card=agent_card)
        print('客户端初始化完成')

        message = Message(
            context_id=str(uuid4()),
            role='user',
            parts=[Part(kind='text', text='打开白色的灯')],
            message_id=uuid4().hex
        )

        try:
            print('正在发送请求...')
            # 修改响应处理方式
            async for response in client.send_message(message):
                # 检查响应类型并处理
                if hasattr(response, 'model_dump'):
                    print('收到响应:', response.model_dump(mode='json', exclude_none=True))
                else:
                    print('收到原始响应:', response)
                    # 如果是元组，尝试提取有用的信息
                    if isinstance(response, tuple):
                        print('元组内容:', response[0] if len(response) > 0 else None)
        except Exception as e:
            print('请求失败:', e)

if __name__ == '__main__':
    asyncio.run(main())