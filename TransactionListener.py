import asyncio
import datetime
from jsonpath_ng import parse
import orjson
from loguru import logger
from websockets import connect
from config import WS_RPC_URL, WALLET_ADDRESS, TRANSACTION_STATUS
from JupiterSwap import JupiterClient

logger.add("app.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip")


def find_first_key_value_jsonpath(data, key):
    jsonpath_expr = parse(f"$..{key}")
    matches = iter(jsonpath_expr.find(data))
    match = next(matches, None)
    return match.value if match else None


def calculate_delay(transaction_data):
    block_time = transaction_data.get('result', {}).get('blockTime')
    if not block_time:
        logger.error("blockTime not found in transaction data.")
        return None

    block_time_dt = datetime.datetime.fromtimestamp(block_time, datetime.UTC)
    current_time_dt = datetime.datetime.now(datetime.UTC)
    delay = (current_time_dt - block_time_dt).total_seconds()
    logger.info(f"blockTime: {block_time_dt}, currentTime: {current_time_dt}, delay: {delay:.2f} seconds")
    return delay


def parse_open_order_data(transaction_data):
    try:

        logger.info(f'transaction_data: {transaction_data}')

        str_data = str(transaction_data)

        if 'Program log: Instruction: Sell' in str_data:
            logger.info('======== SELL ========')
        elif 'Program log: Instruction: Buy' in str_data:
            logger.info('======== BUY ========')
        else:
            logger.info('======== UNKNOWN TRANSACTION ========')

        delay = calculate_delay(transaction_data)
        if delay is not None:
            logger.info(f'delay: {delay:.2f} seconds')

        mint = find_first_key_value_jsonpath(transaction_data, 'mint')
        logger.info(f'mint: {mint}')

        fee = transaction_data.get("result", {}).get("meta", {}).get("fee")
        logger.info(f'fee: {fee}')

        amount = find_first_key_value_jsonpath(transaction_data, 'amount')
        logger.info(f'amount: {amount}')
    except Exception as e:
        logger.error(f"Error processing transaction data: {e}")


class TransactionListener:
    def __init__(self, ws_rpc_url: str, wallet_address: str):
        self.ws_rpc_url = ws_rpc_url
        self.wallet_address = wallet_address
        self.jup = JupiterClient()
        logger.info(f"Check wallet_address: {self.wallet_address}")

    async def _process_logs(self, ws, raw_message: str, commitment: str):
        try:
            message = orjson.loads(raw_message)
        except orjson.JSONDecodeError:
            logger.error(f"Failed to decode message: {raw_message}")
            return

        signature = message.get("params", {}).get("result", {}).get("value", {}).get("signature")
        if signature:
            logger.info(f"===="*50)
            logger.info(f"New transaction detected [{commitment}]: {signature}")
            await self._send_transaction_request(ws, signature, commitment)

    @staticmethod
    async def _send_transaction_request(ws, signature: str, commitment: str):
        subscription_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": commitment,
                    "maxSupportedTransactionVersion": 0
                }
            ]
        }
        logger.info(f"Fetching data for signature: {signature}")
        await ws.send(orjson.dumps(subscription_request).decode("utf-8"))
        raw_response = await ws.recv()
        transaction_data = orjson.loads(raw_response)
        parse_open_order_data(transaction_data)

    async def _subscribe(self, ws, commitment: str):
        subscription_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [self.wallet_address]},
                {"commitment": commitment}
            ]
        }
        logger.info(f"Subscribing to logs with commitment: {commitment}")
        await ws.send(orjson.dumps(subscription_request).decode("utf-8"))
        raw_response = await ws.recv()
        logger.info(f"Subscription confirmed: {raw_response}")

    async def start_listening(self):
        async with connect(self.ws_rpc_url, ping_interval=10, ping_timeout=1) as ws:
            await self._subscribe(ws, TRANSACTION_STATUS)
            async for raw_message in ws:
                await self._process_logs(ws, raw_message, commitment=TRANSACTION_STATUS)


async def main():
    listener = TransactionListener(WS_RPC_URL, WALLET_ADDRESS)
    await listener.start_listening()


if __name__ == '__main__':
    asyncio.run(main())