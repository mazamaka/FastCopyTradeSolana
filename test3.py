import asyncio
import json
from loguru import logger
from websockets import connect

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction

# from solders.instruction import Instruction  # При необходимости
# from solders.system_program import transfer, TransferParams  # Если нужно что-то низкоуровневое

from config import (
    PRIVATE_KEY_STRING,
    WS_RPC_URL,
    HTTP_RPC_URL,
    WALLET_ADDRESS  # Это "адрес кита" или чей?
)

# Ключ, который будет делать «копию» сделки.
SENDER_KEYPAIR = Keypair.from_base58_string(PRIVATE_KEY_STRING)


async def replicate_purchase(client: AsyncClient, original_sig: str, buy_amount: int):
    """
    1. Получаем транзакцию по сигнатуре.
    2. Парсим инструкции, чтобы понять, какую монету купил «кит», по какой цене и т. д.
    3. Формируем новую транзакцию, покупающую ту же монету на 'buy_amount'.
    4. Подписываем и отправляем.
    """
    logger.info(f"Начинаем парсить транзакцию {original_sig} для копирования сделки.")

    tx_info_resp = await client.get_parsed_transaction(original_sig, "confirmed")
    tx_info = tx_info_resp.value

    # Если транзакция не найдена/не обработана
    if not tx_info:
        logger.error("Транзакция не найдена или ещё не попала в обработку нодой.")
        return

    # -----------------------------
    # 1. Смотрим всю parsed-транзакцию
    # -----------------------------
    # Здесь доступны поля:
    #  tx_info.transaction.message.instructions (список инструкций)
    #  tx_info.transaction.signatures
    #  tx_info.meta.postTokenBalances, tx_info.meta.preTokenBalances и т. д.
    #
    # Для Raydium/Serum/Orca их инструкции придётся декодировать. Если это простая
    # SPL-транзакция (перевод токенов), тогда парсим поля "programId", "parsed", "type" и т.д.
    #
    # Пример минимального вывода:
    logger.debug(f"Полные данные о транзакции: {tx_info}")

    instructions = tx_info.transaction.message.instructions
    post_balances = tx_info.meta.postTokenBalances or []
    pre_balances = tx_info.meta.preTokenBalances or []

    # -----------------------------
    # 2. Пытаемся найти логику "покупки токена"
    # -----------------------------
    # В случае Raydium, будет programId = "AmkY...", либо "4Dxx..." (старые версии),
    # или "675kPX9MHTj..." (Raydium v2). Ищем инструкцию "Swap", "Raydium Swap" и т.д.
    #
    # Если это Serum DEX — programId "9xQe...", если Orca — "9W5g...", "WhirLb..." и пр.
    #
    # На самом деле, чтобы детально повторить своп, нужно смотреть не только на сами
    # инструкции, но и на счета-аргументы, кол-во входных/выходных токенов и т. д.
    #
    # Для примера ниже ограничимся "фиктивным" поиском.
    target_instructions = []
    for ix in instructions:
        prog_id = ix["programId"]
        if prog_id in [
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Часто Raydium
            "9xQeWvG816bUx9EPttzWYx4M2AbTfrPs8R9FpNf3kYMW",  # Часто Serum
            # Добавьте при необходимости
        ]:
            target_instructions.append(ix)

    if not target_instructions:
        logger.warning("Не нашли инструкций, похожих на покупку токена. Пропускаем.")
        return

    logger.info(f"Найдено {len(target_instructions)} инструкций, связанных с токен-транзакцией.")

    # ----------------------------------------------------------------
    # 3. На основе разобранных инструкций формируем "новую" покупку
    # ----------------------------------------------------------------
    # Ниже пример «заглушки», где мы создаём новую транзакцию и
    # просто повторяем ТЕ ЖЕ инструкции (при желании можно модифицировать).
    #
    # *Однако* в реальном сценарии нужна детальная декодировка:
    #   - Какие account'ы участвуют.
    #   - Входная монета (SOL или SPL).
    #   - Выходная монета (которую "кит" купил).
    #   - Сумма свопа (buy_amount).
    #
    # И только после этого — корректная сборка инструкций под вашу подпись.
    # ----------------------------------------------------------------

    # Получаем актуальный blockhash
    recent_blockhash_resp = await client.get_latest_blockhash()
    blockhash = recent_blockhash_resp.value.blockhash

    # Допустим, вы хотите "повторить" логику: берём ровно те же инструкции,
    # но меняем feePayer и подписанта на ваш кошелёк.
    # Обратите внимание, что solders.Transaction отличается от solana-py Transaction.
    # Нужно убедиться, что инструкции у вас в формате solders.instruction.Instruction.
    #
    # Так как get_parsed_transaction возвращает инструкции в виде словарей, вам придётся
    # либо вручную конструировать solders-инструкции, либо использовать solana-py.
    # Ниже — псевдокод (примерно), показывающий общую идею.
    #
    # --------------------------------------------------------------------------------
    # ВАРИАНТ 1: Реально декодировать всё вручную и создавать solders.Instruction(...)
    # --------------------------------------------------------------------------------

    # Пример (заглушка — инструкций нет, но показываем, как можно их формировать):
    # from solders.instruction import Instruction, AccountMeta
    replicate_instructions = []
    # for parsed_ix in target_instructions:
    #     program_id = Pubkey.from_string(parsed_ix["programId"])
    #     # Собираем нужные AccountMeta, data и т. д. (это отдельная история)
    #     # ...
    #     replicate_ix = Instruction(
    #         program_id=program_id,
    #         accounts=[...],  # список AccountMeta
    #         data=b"..."      # сериализованные данные
    #     )
    #     replicate_instructions.append(replicate_ix)

    # Для примера сейчас оставим список пустым, чтобы код компилился.

    # Создаём транзакцию
    tx = Transaction.new_with_blockhash(
        instructions=replicate_instructions,
        blockhash=blockhash,
        fee_payer=SENDER_KEYPAIR.pubkey()
    )

    # Подписываем
    tx.sign([SENDER_KEYPAIR])

    # Отправляем
    try:
        result = await client.send_raw_transaction(bytes(tx))
        logger.info(f"Успешно отправили копию сделки. Signature: {result}")
    except Exception as e:
        logger.error(f"Ошибка при отправке копии сделки: {e}")


async def process_logs(raw_message: str, client: AsyncClient):
    """
    Вызывается на каждое новое сообщение по логам.
    Здесь мы:
    1) Читаем сигнатуру транзакции из лога.
    2) Парсим её через `replicate_purchase`.
    """
    logger.info(f"Обрабатываем сообщение: {raw_message}")

    try:
        message = json.loads(raw_message)
    except ValueError:
        logger.warning("Не удалось распарсить JSON из сообщения. Пропускаем.")
        return

    signature = (
        message
        .get("params", {})
        .get("result", {})
        .get("value", {})
        .get("signature")
    )

    if not signature:
        logger.debug("В сообщении нет сигнатуры транзакции. Пропускаем.")
        return

    logger.info(f"Обнаружена транзакция: {signature}")

    # Здесь, например, мы указываем, что хотим "скопировать" сделку на 0.001 SOL,
    # или 1 USDC, или сколько вам нужно. Можно брать из конфигов.
    buy_amount = 1_000_000  # Пример: 0.001 SOL в лампортах

    # Асинхронно вызываем функцию копирования
    await replicate_purchase(client, signature, buy_amount)


async def main():
    """
    Запуск основной логики:
    1. Подключение к WebSocket.
    2. Подписка на "logsSubscribe" по кошельку кита (WALLET_ADDRESS).
    3. Обработка новых логов через process_logs().
    """
    async with connect(WS_RPC_URL, ping_interval=20, ping_timeout=1) as websocket, \
               AsyncClient(HTTP_RPC_URL) as client:
        subscription_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [WALLET_ADDRESS]},  # при упоминании кошелька в логах
                {"commitment": "processed"}
            ]
        }
        await websocket.send(json.dumps(subscription_request))
        raw_response = await websocket.recv()
        logger.info(f"Подтверждение подписки: {raw_response}")

        async for raw_message in websocket:
            # Можно обрабатывать по месту или через create_task().
            # Но для последовательности лучше просто await:
            await process_logs(raw_message, client)


if __name__ == "__main__":
    asyncio.run(main())
