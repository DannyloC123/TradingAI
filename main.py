import asyncio
import os
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

# Load token from tokens.env
load_dotenv("tokens.env")

class XYZ:
    type = 'Stock'
    tickSize = 0.01
    symbolID = 1

class ETF:
    type = 'Fund'
    tickSize = 0.01
    symbolID = 2
    
class ABC:
    type = 'Stock'
    tickSize = 0.01
    symbolID = 3

class DEF:
    type = 'Stock'
    tickSize = 0.01
    symbolID = 4

async def main():
    client = ExchangeClient(
        team_token=os.getenv("TEAM_TOKEN"),
        gateway=GatewayConfig(host=os.getenv("MARKET_HOST")),
        market_data=MarketDataConfig(host=os.getenv("MARKET_HOST"))
    )

    await client.connect()
    print("Connected successfully!")

    # Needed to Submit Order
    order_id = await client.send_new_async(
        client_id=1,                 # internal ID you choose
        symbol_id=XYZ.symbolID,      # choose stock using your class
        side=0,                      # 0 = BUY
        price_ticks=10000,           # $100.00
        quantity=10                  # buy 10 shares
    )
    
    print("Order sent! Order ID:", order_id)

    await client.close()

asyncio.run(main())
