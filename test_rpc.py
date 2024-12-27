import asyncio
from asyncstdlib import enumerate
from solana.rpc.websocket_api import connect

async def main():
    async with connect("wss://api.devnet.solana.com") as websocket:
        await websocket.logs_subscribe()
        first_resp = await websocket.recv()

        # Проверяем тип first_resp
        if hasattr(first_resp, "result"):
            subscription_id = first_resp.result  # Извлекаем значение result
        else:
            print(f"Unexpected response format: {first_resp}")
            return

        print(f"Subscribed with ID: {subscription_id}")

        try:
            async for idx, raw_message in enumerate(websocket):
                if idx >= 10:  # Ограничение для теста
                    break
                print(f"Received message: {raw_message}")
        finally:
            await websocket.logs_unsubscribe(subscription_id)
            print("Unsubscribed and exiting.")

if __name__ == "__main__":
    asyncio.run(main())
