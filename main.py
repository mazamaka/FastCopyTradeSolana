import asyncio
from solana.rpc.api import Client
from solana.rpc.websocket_api import connect
from solders.pubkey import Pubkey
from solders.rpc.config import RpcTransactionLogsFilterMentions
from websockets.exceptions import ConnectionClosedError

WHALE_ADDRESS = Pubkey.from_string("DfMxre4cKmvogbLrPigxmibVTTQDuzjdXojWzjCXXhzj")
HTTP_RPC_URL = "https://api.mainnet-beta.solana.com"
WS_RPC_URL = "wss://api.mainnet-beta.solana.com"
client = Client(HTTP_RPC_URL)


def parse_logs_for_token_purchase(logs: list) -> str | None:
    print("Logs received:", logs)
    return None


def buy_token(token_bought: str):
    print(f"ALERT: need to buy token: {token_bought}")


async def subscribe_to_logs():
    while True:
        try:
            async with connect(
                WS_RPC_URL,
                ping_interval=20,
                ping_timeout=10,
            ) as websocket:
                filter_mentions = RpcTransactionLogsFilterMentions(pubkey=WHALE_ADDRESS)

                req_id = websocket.increment_counter_and_get_id()
                print(f"Sending subscription request with ID {req_id}...")

                subscription_request = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": "logsSubscribe",
                    "params": [
                        {"mentions": [str(WHALE_ADDRESS)]},
                        {"commitment": "confirmed"},
                    ],
                }

                await websocket.send(subscription_request)
                print(f"Subscription request sent: {subscription_request}")

                while True:
                    try:
                        # Получение всех сообщений для отладки
                        message = await websocket.recv()
                        print(f"Received message: {message}")
                    except ConnectionClosedError as e:
                        print(f"Connection closed: {e}")
                        break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)



async def main():
    await subscribe_to_logs()


if __name__ == "__main__":
    asyncio.run(main())
