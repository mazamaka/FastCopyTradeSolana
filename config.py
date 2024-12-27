from dotenv import load_dotenv
import os

# Загрузка переменных окружения из .env
load_dotenv(dotenv_path='.env')

# Чтение переменных
WS_RPC_URL = os.getenv("WS_RPC_URL")
HTTP_RPC_URL = os.getenv("HTTP_RPC_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY_STRING = os.getenv("PRIVATE_KEY_STRING")
DESTINATION_ADDRESS = os.getenv("DESTINATION_ADDRESS")
