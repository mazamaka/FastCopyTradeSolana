import asyncio
import datetime
import time

import orjson
from websockets import connect

from JupiterSwap import JupiterClient
from config import WS_RPC_URL, WALLET_ADDRESS


class TransactionListener:
    def __init__(self, ws_rpc_url: str, wallet_address: str):
        self.ws_rpc_url = ws_rpc_url
        self.wallet_address = wallet_address
        self.jup = JupiterClient()

    async def _process_logs(self, raw_message: str, level: str):
        try:
            message = orjson.loads(raw_message)
            # print(f'{datetime.datetime.now()} message: {message}')
        except orjson.JSONDecodeError:
            print(f"{datetime.datetime.now()} Ошибка декодирования сообщения: {raw_message}")
            return

        signature = (
            message
            .get("params", {})
            .get("result", {})
            .get("value", {})
            .get("signature")
        )
        if signature:
            print(f"{datetime.datetime.now()} [{level}] Новая транзакция: {signature}")
            if level == "processed":
                pass
            if level == "confirmed":
                pass
                # Приоритетная обработка для "processed"
                # await self.get_signature_info(signature)

    async def get_signature_info(self, signature):
        info = await self.jup.get_transaction_info(signature=signature)
        print(f'{datetime.datetime.now()} signature_info: {info}')

    async def _subscribe(self, commitment: str):
        start_time = time.time()
        async with connect(self.ws_rpc_url, ping_interval=10, ping_timeout=1) as ws:
            print(f"{datetime.datetime.now()} Соединение установлено для {commitment}. Подписываемся на DEX...")

            subscription_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [self.wallet_address]},
                    {"commitment": "confirmed"}
                ]
            }

            await ws.send(orjson.dumps(subscription_request).decode("utf-8"))
            raw_response = await ws.recv()
            rtt = (time.time() - start_time) * 1000
            print(f"{datetime.datetime.now()} Подтверждение подписки: {raw_response}, Пинг: {rtt:.2f} ms")

            # Обработка сообщений
            async for raw_message in ws:
                await self._process_logs(raw_message, level=commitment)


    async def start_listening(self):
        # Запуск двух параллельных подписок
        await asyncio.gather(
            self._subscribe("confirmed"),
            self._subscribe("processed")
        )


async def main():
    listener = TransactionListener(WS_RPC_URL, WALLET_ADDRESS)
    await listener.start_listening()

if __name__ == '__main__':
    asyncio.run(main())
