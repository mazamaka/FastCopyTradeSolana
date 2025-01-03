import asyncio
import datetime
from enum import Enum

from jsonpath_ng import parse
import orjson
from loguru import logger
from websockets import connect
from config import WS_RPC_URL, WALLET_ADDRESS, TRANSACTION_STATUS
from JupiterSwap import JupiterClient

logger.add("app.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip")

check_program_ids = ['6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P', '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8']


def find_first_key_value_jsonpath(data, key):
    jsonpath_expr = parse(f"$..{key}")
    matches = iter(jsonpath_expr.find(data))
    match = next(matches, None)
    return match.value if match else None

def find_all_key_values_jsonpath(data, key):
    jsonpath_expr = parse(f"$..{key}")
    values = [match.value for match in jsonpath_expr.find(data)]
    return values


def calculate_delay(transaction_data):
    block_time = transaction_data.get('result', {}).get('blockTime')
    if not block_time:
        logger.error("blockTime not found in transaction data.")
        return None
    block_time_dt = datetime.datetime.fromtimestamp(block_time, datetime.UTC)
    current_time_dt = datetime.datetime.now(datetime.UTC)
    delay = (current_time_dt - block_time_dt).total_seconds()
    # logger.info(f"blockTime: {block_time_dt}, currentTime: {current_time_dt}, delay: {delay:.2f} seconds")
    # logger.info(f'delay: {delay:.2f} seconds')
    return delay

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"

def get_transaction_type(transaction_data) -> TransactionType:
    pre_balances = find_first_key_value_jsonpath(transaction_data, 'preTokenBalances') or []
    post_balances = find_first_key_value_jsonpath(transaction_data, 'postTokenBalances') or []

    transaction_type = TransactionType.UNKNOWN

    for pre, post in zip(pre_balances, post_balances):
        if pre.get("owner") == WALLET_ADDRESS:
            pre_amount = int(pre["uiTokenAmount"]["amount"])
            post_amount = int(post["uiTokenAmount"]["amount"])
            if post_amount > pre_amount:
                transaction_type = TransactionType.BUY
            elif post_amount < pre_amount:
                transaction_type = TransactionType.SELL

    if transaction_type == TransactionType.UNKNOWN:
        str_data = str(transaction_data)
        if 'Program log: Instruction: Sell' in str_data:
            transaction_type = TransactionType.SELL
        elif 'Program log: Instruction: Buy' in str_data:
            transaction_type = TransactionType.BUY

    # logger.info(f"Transaction type detected: {transaction_type.value}")
    return transaction_type


def check_program_addresses(transaction_data: dict) -> bool:
    program_ids = find_all_key_values_jsonpath(transaction_data, 'programId')
    for check_program_id in check_program_ids:
        if check_program_id in program_ids:
            # logger.info(f'program_ids: {program_ids}')
            return True
    return False


def get_token_address(transaction_data):
    token_address = None
    pre_balances = find_first_key_value_jsonpath(transaction_data, 'preTokenBalances')
    for pre in pre_balances:
        if pre["owner"] == WALLET_ADDRESS:
            token_address = pre["mint"]
    if not token_address:
        token_address = find_first_key_value_jsonpath(transaction_data, 'mint')
    return token_address

def get_fee(transaction_data):
    fee = transaction_data.get("result", {}).get("meta", {}).get("fee")
    # logger.info(f'fee: {fee}')
    return fee

def get_amount(transaction_data):
    amount = find_first_key_value_jsonpath(transaction_data, 'amount')
    # logger.info(f'amount: {amount}')
    return amount

def parse_open_order_data(transaction_data):
    try:

        # logger.info(f'transaction_data: {transaction_data}')

        transaction_type = get_transaction_type(transaction_data)

        check_program = check_program_addresses(transaction_data)

        delay = calculate_delay(transaction_data)

        token_address = get_token_address(transaction_data)

        fee = get_fee(transaction_data)

        amount = get_amount(transaction_data)

        if TransactionType.UNKNOWN != transaction_type:
            if check_program:
                if token_address:
                    if fee:
                        if amount:
                            order_data = {
                                "transaction_type": transaction_type.value,
                                "check_program": check_program,
                                "delay": delay,
                                "token_address": token_address,
                                "fee": fee,
                                "amount": amount
                            }

                            logger.info(f'==' * 50)
                            logger.info(f'order_data: {order_data}')
                            logger.info(f'==' * 50 + '\n')

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
    async def _send_transaction_request(ws, signature: str, commitment: str, max_retries: int = 10,
                                        delay_between_retries: float = 0.1):
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

        retries = 0
        while retries < max_retries:
            logger.info(f"Fetching data for signature: {signature}, attempt: {retries + 1}")
            await ws.send(orjson.dumps(subscription_request).decode("utf-8"))
            raw_response = await ws.recv()
            transaction_data = orjson.loads(raw_response)

            if transaction_data.get("result") is not None:
                parse_open_order_data(transaction_data)
                return

            logger.warning(f"No result for transaction: {signature}. Retrying...")
            retries += 1
            await asyncio.sleep(delay_between_retries)

        logger.error(f"Failed to fetch valid transaction data for signature: {signature} after {max_retries} attempts.")

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

    async def start_check_signatures(self, signatures):
        async with connect(self.ws_rpc_url, ping_interval=10, ping_timeout=1) as ws:
            for signature in signatures:
                await self._send_transaction_request(ws, signature, commitment=TRANSACTION_STATUS)

def parse_transaction_logs(file_path):
    signatures = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            if 'New transaction detected [confirmed]: ' in line:
                signature = line.split('New transaction detected [confirmed]: ')[1]
                signatures.append(signature.strip())

    return signatures

async def main():
    listener = TransactionListener(WS_RPC_URL, WALLET_ADDRESS)
    await listener.start_listening()

    # file_path = "_007_transaction_listener_logs(13).txt"
    # signatures = parse_transaction_logs(file_path)
    # # signatures = [signatures[3]]
    # # signatures = ['2SDa3FxmrAsRFmXte1X6mWda5AKR8RZRfJPWMJSTPcRLfGiVNUG8XWJV2JTDfbRTqAx8rQxVkAgVsv2injf47smb']
    # await listener.start_check_signatures(signatures=signatures)
    # print(f"Parsed {len(signatures)} signatures.")


if __name__ == '__main__':
    asyncio.run(main())