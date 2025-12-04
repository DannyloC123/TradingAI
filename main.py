import asyncio
import os
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

# Load token from tokens.env
load_dotenv("tokens.env")

# ---------------- SYMBOL CLASSES -----------------

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

# -------------- TRADING FUNCTIONS -----------------

async def buy(client, symbol, price_dollars, quantity, client_id):
    """Place a BUY order."""
    price_ticks = int(price_dollars * 100)  # convert dollars → cents
    return await client.send_new_async(
        client_id=client_id,
        symbol_id=symbol.symbolID,
        side=0,                 # BUY
        price_ticks=price_ticks,
        quantity=quantity
    )

async def sell(client, symbol, price_dollars, quantity, client_id):
    """Place a SELL order."""
    price_ticks = int(price_dollars * 100)
    return await client.send_new_async(
        client_id=client_id,
        symbol_id=symbol.symbolID,
        side=1,                 # SELL
        price_ticks=price_ticks,
        quantity=quantity
    )

# -------------- MAIN PROGRAM ----------------------

async def main():
    client = ExchangeClient(
        team_token=os.getenv("TEAM_TOKEN"),
        gateway=GatewayConfig(host=os.getenv("MARKET_HOST")),
        market_data=MarketDataConfig(host=os.getenv("MARKET_HOST"))
    )

    await client.connect()
    print("Connected successfully!")

    # Example trades:
    order1 = await buy(client, XYZ, price_dollars=100.00, quantity=10, client_id=1)
    print("BUY order sent:", order1)

    order2 = await sell(client, ABC, price_dollars=50.25, quantity=5, client_id=2)
    print("SELL order sent:", order2)

    await client.close()

asyncio.run(main())
