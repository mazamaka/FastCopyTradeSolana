# FastCopyTradeSolana

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Solana](https://img.shields.io/badge/Solana-Mainnet-9945FF?logo=solana&logoColor=white)
![Jupiter](https://img.shields.io/badge/Jupiter-v6-E8AC2E?logo=data:image/svg+xml;base64,&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Fast Solana copy-trading bot with automated trade analysis and execution. Monitors a target wallet's on-chain activity via WebSocket, detects swaps on major DEX programs (Raydium, Pump.fun), and mirrors trades through Jupiter Aggregator.

---

## Features

- **Real-time WebSocket monitoring** -- subscribes to on-chain logs for a target wallet using Solana's `logsSubscribe` RPC method
- **Transaction parsing** -- extracts token mints, amounts, fees, and determines trade direction (BUY/SELL) from `preTokenBalances` / `postTokenBalances`
- **DEX program detection** -- identifies swaps routed through Raydium and Pump.fun
- **Jupiter v6 integration** -- executes market swaps, limit orders, and DCA strategies via the Jupiter Python SDK
- **Latency tracking** -- calculates delay between block time and detection time to measure copy-trade speed
- **Auto-retry mechanism** -- retries transaction fetching with configurable attempts and delay
- **Structured logging** -- uses Loguru with file rotation and compression
- **Docker support** -- production-ready Dockerfile included

## Architecture

```
TransactionListener (WebSocket)
    |
    |--> logsSubscribe(target_wallet)
    |--> on new signature --> getTransaction(jsonParsed)
    |--> parse_open_order_data()
    |       |- get_transaction_type() -> BUY / SELL
    |       |- check_program_addresses() -> Raydium / Pump.fun
    |       |- get_token_address()
    |       |- calculate_delay()
    |
    +--> JupiterClient.swap() --> execute copy trade
```

## Quick Start

### Prerequisites

- Python 3.13+
- Solana wallet with SOL balance
- RPC provider (QuikNode, Helius, or public endpoint)

### Installation

```bash
git clone https://github.com/mazamaka/FastCopyTradeSolana.git
cd FastCopyTradeSolana

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Description |
|----------|-------------|
| `WS_RPC_URL` | WebSocket RPC endpoint (`wss://...`) |
| `HTTP_RPC_URL` | HTTP RPC endpoint (`https://...`) |
| `WALLET_ADDRESS` | Target wallet to copy-trade |
| `PRIVATE_KEY_STRING` | Your wallet private key (base58) |
| `DESTINATION_ADDRESS` | Destination address for transfers |
| `TRANSACTION_STATUS` | Commitment level: `confirmed` (recommended) |

> **Warning:** Never share or commit your `PRIVATE_KEY_STRING`. Use a dedicated wallet with limited funds.

### Run

```bash
python TransactionListener.py
```

The bot will connect to the WebSocket RPC, subscribe to the target wallet's logs, and start monitoring for trades.

### Docker

```bash
docker build -t fast-copy-trade .
docker run --env-file .env fast-copy-trade
```

## Project Structure

```
.
├── TransactionListener.py   # Main entry point -- WebSocket listener & transaction parser
├── JupiterSwap.py           # Jupiter v6 client -- swap, limit orders, DCA
├── config.py                # Environment variable loader
├── main.py                  # Standalone log subscription example
├── Dockerfile               # Production container
├── requirements.txt         # Pinned dependencies
├── .env.example             # Environment template
└── test_*.py                # Development test scripts
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `solana` / `solders` | Solana RPC client and transaction primitives |
| `jupiter-python-sdk` | Jupiter Aggregator v6 API |
| `websockets` | Low-level WebSocket connection |
| `orjson` | Fast JSON parsing |
| `loguru` | Structured logging |
| `jsonpath-ng` | JSONPath queries for transaction data |
| `base58` | Key encoding/decoding |

## Disclaimer

This software is provided for **educational and research purposes only**. Copy-trading involves significant financial risk. The authors are not responsible for any financial losses incurred through the use of this bot. Always test with small amounts first and never risk funds you cannot afford to lose.

## Author

**Maksym Babenko**

- GitHub: [@mazamaka](https://github.com/mazamaka)
- Telegram: [@Mazamaka](https://t.me/Mazamaka)

## License

This project is licensed under the MIT License.
