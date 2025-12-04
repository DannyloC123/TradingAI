import asyncio
import os
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

# Load token from tokens.env
load_dotenv("tokens.env")

async def main():
    client = ExchangeClient(
        team_token=os.getenv("TEAM_TOKEN"),
        gateway=GatewayConfig(host="MARKET_HOST"),
        market_data=MarketDataConfig(host="MARKET_HOST")
    )

    await client.connect()
    print("Connected successfully!")
    await client.close()

asyncio.run(main())
