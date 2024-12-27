import asyncio
import json
from solana.rpc.websocket_api import connect
from solders.pubkey import Pubkey

WHALE_ADDRESS = Pubkey.from_string("DfMxre4cKmvogbLrPigxmibVTTQDuzjdXojWzjCXXhzj")
WS_RPC_URL = "wss://api.devnet.solana.com"


def parse_logs_for_token_purchase(logs: list) -> str | None:
    print("Logs received:", logs)
    return None


def buy_token(token_bought: str):
    print(f"ALERT: need to buy token: {token_bought}")


async def process_logs(websocket):
    async for raw_message in websocket:
        try:
            message = json.loads(raw_message)
            print(f"Received message: {message}")

            # Проверяем наличие логов
            params = message.get("params", {})
            result = params.get("result", {})
            logs = result.get("logs", [])

            token_to_buy = parse_logs_for_token_purchase(logs)
            if token_to_buy:
                buy_token(token_to_buy)
        except Exception as e:
            print(f"Error processing message: {e}")


async def subscribe_to_logs():
    async with connect(WS_RPC_URL) as websocket:
        subscription_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [{"mentions": [str(WHALE_ADDRESS)]}, {"commitment": "confirmed"}]
        }

        print(f"Sending subscription request: {subscription_request}")
        await websocket.send(json.dumps(subscription_request))

        # Получаем ответ на подписку
        raw_response = await websocket.recv()
        response = json.loads(raw_response)
        print(f"Subscription response: {response}")

        if "result" not in response:
            print("Subscription failed.")
            return

        subscription_id = response["result"]
        print(f"Subscribed with ID: {subscription_id}")

        try:
            # Обрабатываем входящие логи
            await process_logs(websocket)
        except Exception as e:
            print(f"Error while processing logs: {e}")
        finally:
            unsubscribe_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "logsUnsubscribe",
                "params": [subscription_id]
            }
            print(f"Sending unsubscribe request: {unsubscribe_request}")
            await websocket.send(json.dumps(unsubscribe_request))


async def main():
    while True:
        try:
            await subscribe_to_logs()
        except Exception as e:
            print(f"Error in subscription: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
