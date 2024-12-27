import base58
import base64
import json
from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed
from jupiter_python_sdk.jupiter import Jupiter


class JupiterClient:
    def __init__(self, rpc_url: str, private_key: str):
        self.client = AsyncClient(rpc_url)
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
