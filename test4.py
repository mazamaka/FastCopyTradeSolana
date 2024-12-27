import requests

HTTP_RPC_URL = "https://api.mainnet-beta.solana.com"
WALLET_ADDRESS = "REMOVED_DESTINATION_ADDRESS"

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getSignaturesForAddress",
    "params": [WALLET_ADDRESS, {"limit": 10}]
}

if __name__ == "__main__":
    response = requests.post(HTTP_RPC_URL, json=payload)
    print(response.json())

