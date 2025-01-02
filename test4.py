import base58

class Subscription:
    def __init__(self, wallet_address):
        self.wallet_address = wallet_address

    def create_subscription_request(self):
        encoded_address = base58.b58encode(self.wallet_address.encode()).decode()
        print(f"Encoded address: {encoded_address}")
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "programSubscribe",
            "params": [
                "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
                {
                    "encoding": "jsonParsed",
                    "filters": [
                        {
                            "memcmp": {
                                "offset": 32,
                                "bytes": encoded_address
                            }
                        }
                    ],
                    "commitment": "confirmed"
                }
            ]
        }



if __name__ == "__main__":
    # Пример использования
    wallet_address = "REMOVED_WALLET_ADDRESS"
    subscription = Subscription(wallet_address)
    subscription_request = subscription.create_subscription_request()
    print(subscription_request)

