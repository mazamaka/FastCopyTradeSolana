import asyncio
import websockets
import json


async def listen_to_socket():
    url = "wss://ws.gmgn.ai/stream?_t=true&uuid=872fa50fb78dab41"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive, Upgrade",
        "Host": "ws.gmgn.ai",
        "Origin": "https://gmgn.ai",
        "Pragma": "no-cache",
        "Sec-WebSocket-Extensions": "permessage-deflate",
        "Sec-WebSocket-Key": "jewerbCSO3PAFzwRSVByRQ==",
        "Sec-WebSocket-Version": "13",
        "Upgrade": "websocket",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    }

    try:
        async with websockets.connect(url, extra_headers=headers) as websocket:
            print("Подключение установлено.")

            # Пример отправки подписки на канал
            subscription_message = {
                "action": "subscribe",
                "channel": "wallet_activity",
                "data": {
                    "chain": "sol",
                    "wallet": "YOUR_WALLET_ADDRESS",
                },
            }

            await websocket.send(json.dumps(subscription_message))

            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Получено сообщение: {json.dumps(data, indent=2)}")
                except websockets.ConnectionClosed as e:
                    print(f"Соединение закрыто: {e}")
                    break
                except json.JSONDecodeError as e:
                    print(f"Ошибка декодирования сообщения: {e}")
    except Exception as e:
        print(f"Ошибка подключения: {e}")


if __name__ == "__main__":
    asyncio.run(listen_to_socket())
