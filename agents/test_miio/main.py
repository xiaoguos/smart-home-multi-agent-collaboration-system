
import logging
import asyncio
import json
from uuid import uuid4
import httpx
from a2a.client import ClientFactory, A2ACardResolver
from a2a.types import Message, Part
from a2a.client.client import ClientConfig

async def main():
    logging.basicConfig(level=logging.INFO)

    base_url = 'http://localhost:12000'

    async with httpx.AsyncClient(timeout=180.0) as httpx_client:
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
            parts=[Part(kind='text', text='')],
            message_id=uuid4().hex
        )

        try:
            # 修改响应处理方式
            response_count = 0
            async for response in client.send_message(message):
                response_count += 1
                print(f'\n--- 响应 #{response_count} ---')
                
                # 检查响应类型并处理
                if hasattr(response, 'model_dump'):
                    response_data = response.model_dump(mode='json', exclude_none=True)
                    
                    # 美化输出
                    if isinstance(response_data, dict):
                        # 提取关键信息
                        if 'parts' in response_data:
                            for part in response_data['parts']:
                                if isinstance(part, dict) and 'text' in part:
                                    print('内容:', part['text'])
                        else:
                            print('完整响应:', json.dumps(response_data, ensure_ascii=False, indent=2))
                    else:
                        print('响应:', response_data)
                else:
                    print('原始响应:', response)
                    # 如果是元组，尝试提取有用的信息
                    if isinstance(response, tuple):
                        print('元组内容:', response[0] if len(response) > 0 else None)
            
            print('=' * 80)
            print(f'共收到 {response_count} 个响应')
            
        except asyncio.TimeoutError:
            print('\n❌ 请求超时！可能的原因：')
            print('  1. conductor_agent 未启动（运行: python agents/conductor_agent/main.py）')
            print('  2. 获取小米设备信息耗时过长')
            print('  3. 网络连接问题')
        except Exception as e:
            print(f'\n❌ 请求失败: {type(e).__name__}: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())