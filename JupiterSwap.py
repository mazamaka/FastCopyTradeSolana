import asyncio
import datetime
from typing import Optional, Dict, Any

import base58
import base64
import json

import orjson
from asyncstdlib import await_each
from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed
from jupiter_python_sdk.jupiter import Jupiter

from config import HTTP_RPC_URL, PRIVATE_KEY_STRING


class JupiterClient:
    def __init__(self, rpc_url: str = HTTP_RPC_URL, private_key: str = PRIVATE_KEY_STRING):
        self.client = AsyncClient(endpoint=rpc_url)
        self.keypair = Keypair.from_bytes(base58.b58decode(private_key))
        self.jupiter = Jupiter(
            async_client=self.client,
            keypair=self.keypair,
            quote_api_url="https://quote-api.jup.ag/v6/quote?",
            swap_api_url="https://quote-api.jup.ag/v6/swap",
            open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
            cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
            query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
            query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
            query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory",
        )

    async def swap(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 1) -> str:
        transaction_data = await self.jupiter.swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=slippage_bps,
        )
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = self.keypair.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await self.client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_id = json.loads(result.to_json())["result"]
        return transaction_id

    async def open_limit_order(self, input_mint: str, output_mint: str, in_amount: int, out_amount: int) -> str:
        transaction_data = await self.jupiter.open_order(
            input_mint=input_mint,
            output_mint=output_mint,
            in_amount=in_amount,
            out_amount=out_amount,
        )
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data["transaction_data"]))
        signature = self.keypair.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature, transaction_data["signature2"]])
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await self.client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_id = json.loads(result.to_json())["result"]
        return transaction_id

    async def create_dca_account(
        self,
        input_mint: str,
        output_mint: str,
        total_in_amount: int,
        in_amount_per_cycle: int,
        cycle_frequency: int,
    ) -> dict:
        return await self.jupiter.dca.create_dca(
            input_mint=Pubkey.from_string(input_mint),
            output_mint=Pubkey.from_string(output_mint),
            total_in_amount=total_in_amount,
            in_amount_per_cycle=in_amount_per_cycle,
            cycle_frequency=cycle_frequency,
            min_out_amount_per_cycle=0,
            max_out_amount_per_cycle=0,
            start=0,
        )

    async def close_dca_account(self, dca_pubkey: str) -> str:
        return await self.jupiter.dca.close_dca(dca_pubkey=Pubkey.from_string(dca_pubkey))

    async def get_transaction_info(self, signature: str):
        sig_bytes = base58.b58decode(signature)
        while True:
            tx_sig = Signature(sig_bytes)
            transaction_data = await self.client.get_transaction(tx_sig) #, encoding="json"
            # print(f'transaction_data.value: {transaction_data.value}')
            if hasattr(transaction_data.value, 'transaction'):

                print(f'{datetime.datetime.now()} {transaction_data.value.transaction}')

                # signatures = transaction_data.value.transaction.meta
                #
                # print(f'signatures: {signatures}')

                if transaction_data:
                    # print(f'transaction_data: {transaction_data}')
                    # print(f'transaction_data: {type(transaction_data)}')
                    result = orjson.loads(transaction_data.to_json()).get("result")
                    # print(f'result: {result}')
                    # self.debug_transaction_structure(transaction_data)
                    # await self.parse_transaction(result)
                    break
            print(f'== sleep ==')
            await asyncio.sleep(1)

    async def parse_transaction(self, transaction_data):
        print(f'transaction_data: {transaction_data}')
        try:
            # Извлечение подписи транзакции
            tx_signature = transaction_data["transaction"]["signatures"][0]

            # Извлечение необходимых данных
            pre_balances = transaction_data["meta"]["preTokenBalances"]
            post_balances = transaction_data["meta"]["postTokenBalances"]

            # Найти используемые токены и их количество
            input_token = self._find_input_token(pre_balances, post_balances)
            output_token = self._find_output_token(pre_balances, post_balances)
            amount = self._calculate_token_amount(pre_balances, post_balances, input_token)

            tr = {
                "input_mint": input_token["mint"],
                "output_mint": output_token["mint"],
                "amount": amount,
                "tx_signature": tx_signature
            }

            print(f'tr: {tr}')

            return tr
        except Exception as e:
            print(f"Ошибка при парсинге транзакции: {e}")
            return None

    def _find_input_token(self, pre_balances, post_balances):
        for pre, post in zip(pre_balances, post_balances):
            if int(pre["uiTokenAmount"]["amount"]) > int(post["uiTokenAmount"]["amount"]):
                return pre
        return None

    def _find_output_token(self, pre_balances, post_balances):
        for pre, post in zip(pre_balances, post_balances):
            if int(pre["uiTokenAmount"]["amount"]) < int(post["uiTokenAmount"]["amount"]):
                return post
        return None

    def _calculate_token_amount(self, pre_balances, post_balances, token):
        for pre, post in zip(pre_balances, post_balances):
            if pre["mint"] == token["mint"]:
                return int(post["uiTokenAmount"]["amount"]) - int(pre["uiTokenAmount"]["amount"])
        return 0


async def main():
    jup = JupiterClient()
    signature = '4ESYyEMmWc4GzbWQjuXTfgwhQBTB4ocWP8GGNFe5e8oTs9cBsg4eHK2onQPqmwkc4w493m17Egb9i1zbkzuj4ovw'
    await jup.get_transaction_info(signature=signature)


if __name__ == '__main__':
    asyncio.run(main())


