import asyncio
import os
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig
import httpx
import asyncio
from random import random
import time
import json
import numpy as np
import collections


# Load token from tokens.env
load_dotenv("tokens.env")

EXCHANGE_HOST = "159.65.173.202"


# -------------- TRADING FUNCTIONS -----------------

async def buy(client, symbol, price_dollars, quantity, client_id):
    try:
        price_ticks = int(price_dollars * 100)
        order_id = await client.send_new_async(
            client_id=client_id,
            symbol_id=symbol.symbolID,
            side=0,
            price_ticks=price_ticks,
            quantity=quantity
        )
        print(f"[BUY] {symbol.ticker} @ ${price_dollars:.2f} x{quantity} | order_id={order_id}")
        return order_id
    except Exception as e:
        print(f"[BUY ERROR] {e}")


async def sell(client, symbol, price_dollars, quantity, client_id):
    try:
        price_ticks = int(price_dollars * 100)
        order_id = await client.send_new_async(
            client_id=client_id,
            symbol_id=symbol.symbolID,
            side=1,
            price_ticks=price_ticks,
            quantity=quantity
        )
        print(f"[SELL] {symbol.ticker} @ ${price_dollars:.2f} x{quantity} | order_id={order_id}")
        return order_id
    except Exception as e:
        print(f"[SELL ERROR] {e}")


async def get_bid_ask(symbol):
    async with httpx.AsyncClient(timeout=1.0) as client:  
        for _ in range(5):      # retry up to 5 times
            try:
                r = await client.get(f"http://{EXCHANGE_HOST}:8081/quotes")
                data = r.json()
                bid = data[symbol]["bid"]
                ask = data[symbol]["ask"]
                return bid, ask
            except Exception as e:
                print(f"[WARN] quote fetch failed for {symbol}, retrying... {e}")
                await asyncio.sleep(0.1)

    print(f"[ERROR] get_bid_ask() failed permanently for {symbol}")
    return None, None

    
async def get_workbook(symbol):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://{EXCHANGE_HOST}:8081/orderbook/{symbol}"
        )
        orderbook = response.json()

        print(f"\nFull orderbook for {symbol}:")
        print(json.dumps(orderbook, indent=4))   # <-- PRINT ENTIRE THING


async def get_recent_trades(symbol):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://{EXCHANGE_HOST}:8081/trades/recent?symbol={symbol}&limit=1000"
        )
        data = response.json()

        print(f"\nNumber of trades returned: {len(data['trades'])}")

        return data["trades"]

        # 🔍 Full raw JSON
        #print(f"\nFull recent trades data for {symbol}:")
        #print(json.dumps(data, indent=4))

        # 🔍 Human-readable formatted list
        #print(f"\nFormatted list:")
        #for idx, trade in enumerate(data['trades'], start=1):
            #print(f"{idx} {trade['side']} {trade['quantity']} @ ${trade['price']:.2f}")

price_history = []       # stores live prices
WINDOW = 50              # moving average window size (change as needed)


async def get_average_price(symbol):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://{EXCHANGE_HOST}:8081/trades/recent?symbol={symbol}&limit=1000"
        )
        data = response.json()
        trades = data["trades"]

        if not trades:
            return None, None

        # Extract all recent trade prices
        prices = [t["price"] for t in trades]
        recent_avg = sum(prices) / len(prices)      # average of recent trades

        # Get the newest price only
        latest_price = trades[0]["price"]

        # Store newest price into history
        price_history.append(latest_price)

        # If history is longer than window, trim it
        if len(price_history) > WINDOW:
            price_history.pop(0)

        # Compute moving average
        moving_avg = sum(price_history) / len(price_history)

        return recent_avg, moving_avg

# returns current price, order book depth, and recent trades for another symbol
async def get_market_data():
    async with httpx.AsyncClient() as client:
        # Get current quotes (best bid/ask for all symbols)
        response = await client.get(f"http://{EXCHANGE_HOST}:8081/quotes")
        quotes = response.json()
        
        for symbol, data in quotes.items():
            if data['bid'] and data['ask']:
                print(f"{symbol}: ${data['bid']:.2f} / ${data['ask']:.2f}")
                print(f"  Spread: ${data['ask'] - data['bid']:.2f}")
        
        # Get 10-level orderbook depth
        response = await client.get(f"http://{EXCHANGE_HOST}:8081/orderbook/ETF")
        orderbook = response.json()
        
        print(f"\nETF Orderbook:")
        print(f"Best bid: ${orderbook['bids'][0]['price']:.2f} x {orderbook['bids'][0]['quantity']}")
        print(f"Best ask: ${orderbook['asks'][0]['price']:.2f} x {orderbook['asks'][0]['quantity']}")
        
        # Get recent trades for specific symbol
        response = await client.get(
            f"http://{EXCHANGE_HOST}:8081/trades/recent?symbol=XYZ&limit=10"
        )
        data = response.json()
        for trade in data['trades']:
            print(f"{trade['side']} {trade['quantity']} @ ${trade['price']:.2f}")

#asyncio.run(get_market_data())

# ---------------- SYMBOL CLASSES -----------------
run_time = 7200         # 7200 seconds = 2 hours
test_time = 5

class XYZ:
    ticker = "XYZ"
    type = 'Stock'
    tickSize = 0.01
    symbolID = 1


    async def run(self):
        for x in range(run_time):
            bid, ask = await get_bid_ask("XYZ")
            print(f"XYZ Bid: {bid}, Ask: {ask}")
            await asyncio.sleep(1)

class ETF:
    ticker = "ETF"
    type = 'Fund'
    tickSize = 0.01
    symbolID = 2

    async def run(self):
        for x in range(run_time):
            bid, ask = await get_bid_ask("ETF")
            print(f"ETF Bid: {bid}, Ask: {ask}")
            await asyncio.sleep(1)

class ABC:
    ticker = "ABC"
    type = 'Stock'
    tickSize = 0.01
    symbolID = 3

    async def run(self):
        for x in range(run_time):
            bid, ask = await get_bid_ask("ABC")
            print(f"ABC Bid: {bid}, Ask: {ask}")
            await asyncio.sleep(1)

class DEF:
    ticker = "DEF"
    type = 'Stock'
    tickSize = 0.01
    symbolID = 4

    async def run(self):
        for x in range(run_time):
            bid, ask = await get_bid_ask("DEF")
            print(f"DEF Bid: {bid}, Ask: {ask}")
            await asyncio.sleep(1)

# ---------------- STRATEGY IMPLEMENTATION -----------------

class MeanReversionBot:
    def __init__(self, client, symbol_obj):
        self.client = client
        self.symbol = symbol_obj

        # strategy parameters
        self.history_len = 20   # number of past prices to keep for average
        self.price_history = collections.deque(maxlen=self.history_len)

        self.max_pos_dollars = 100000
        self.small_pos_pct = 0.30   # 30%

        # state tracking
        self.current_tier = 0
        self.side = None 
    
    async def run(self):
        client_req_id = 1000
        print(f"--- Starting Mean Reversion Bot for {self.symbol.ticker} ---", flush=True)

        while True:
            # market data
            bid, ask = await get_bid_ask(self.symbol.ticker)
            
            # If the exchange returns no data (rare, but possible)
            if bid is None or ask is None:
                print("Waiting for quotes...", flush=True)
                await asyncio.sleep(1)
                continue
            
            # calculate mid-price
            current_price = (bid + ask) / 2

            # update history
            self.price_history.append(current_price)

            # --- THE FIX IS HERE ---
            # If we don't have 20 prices yet, print progress so we know it's working
            if len(self.price_history) < self.history_len:
                print(f"[Warmup] Collecting data... {len(self.price_history)}/{self.history_len} | Price: ${current_price:.2f}", flush=True)
                await asyncio.sleep(1)
                continue
            
            # -----------------------

            avg_price = np.mean(self.price_history)
            deviation = current_price - avg_price

            # Print status every second so you know it's alive
            print(f"Price: ${current_price:.2f} | Mean: ${avg_price:.2f} | Dev: ${deviation:+.2f}", flush=True)

            # check thresholds
            # === MEAN REVERSION TRADING LOGIC ===

            # FULL SHORT (overpriced)
            if deviation >= 0.80:
                if self.current_tier != 2 or self.side != 'SHORT':
                    print(f">>> FULL SHORT at bid {bid}")
                    qty = int(self.max_pos_dollars / current_price)
                    await sell(self.client, self.symbol, bid, qty, client_req_id)
                    self.current_tier = 2
                    self.side = 'SHORT'
                    client_req_id += 1

            # SMALL SHORT
            elif deviation >= 0.30:
                if self.current_tier == 0:
                    print(f"> SMALL SHORT at bid {bid}")
                    qty = int((self.max_pos_dollars * self.small_pos_pct) / current_price)
                    await sell(self.client, self.symbol, bid, qty, client_req_id)
                    self.current_tier = 1
                    self.side = 'SHORT'
                    client_req_id += 1

            # FULL LONG (undervalued)
            elif deviation <= -0.80:
                if self.current_tier != 2 or self.side != 'LONG':
                    print(f">>> FULL LONG at ask {ask}")
                    qty = int(self.max_pos_dollars / current_price)
                    await buy(self.client, self.symbol, ask, qty, client_req_id)
                    self.current_tier = 2
                    self.side = 'LONG'
                    client_req_id += 1

            # SMALL LONG
            elif deviation <= -0.30:
                if self.current_tier == 0:
                    print(f"> SMALL LONG at ask {ask}")
                    qty = int((self.max_pos_dollars * self.small_pos_pct) / current_price)
                    await buy(self.client, self.symbol, ask, qty, client_req_id)
                    self.current_tier = 1
                    self.side = 'LONG'
                    client_req_id += 1


            await asyncio.sleep(1)

                


# -------------- MAIN PROGRAM ----------------------

async def main():
    # test variables
    #num_stock = random.randint(1,100)
    #time_interval = random.randint(1, 36000)

    client = ExchangeClient(
        team_token=os.getenv("TEAM_TOKEN"),
        gateway=GatewayConfig(host=os.getenv("MARKET_HOST")),
        market_data=MarketDataConfig(host=os.getenv("MARKET_HOST"))
    )

    await client.connect()
    print("Connected successfully!")

    # Create all bots
    bot_xyz = MeanReversionBot(client, XYZ())
    bot_etf = MeanReversionBot(client, ETF())
    bot_abc = MeanReversionBot(client, ABC())
    bot_def = MeanReversionBot(client, DEF())

    # Run all at the same time
    await asyncio.gather(
        bot_xyz.run(),
        bot_etf.run(),
        bot_abc.run(),
        bot_def.run()
    )
    # Example trades:
    #order1 = await buy(client, XYZ, price_dollars=0, quantity=200, client_id=1)
    #print("BUY order sent:", order1)

    #order2 = await sell(client, ABC, price_dollars=50.25, quantity=5, client_id=2)
    #print("SELL order sent:", order2)

    await client.close()

asyncio.run(main())


async def main():
    # Connect using real team token
    client = ExchangeClient(
        team_token=os.getenv("TEAM_TOKEN"),
        gateway=GatewayConfig(host=EXCHANGE_HOST),
        market_data=MarketDataConfig(host=EXCHANGE_HOST)
    )

    await client.connect()
    print("Connected to exchange!")

    # BUY 5 shares of XYZ at the current ASK
    resp = await client.send_new_async(
        client_id=1,
        symbol_id=1,         # XYZ
        side=0,              # 0 = BUY
        price_ticks=10000,   # $100.00 (SAFE price inside collar)
        quantity=5
    )

    print("Order submitted! order_id =", resp)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())




'''
import asyncio
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

TEAM_TOKEN = "stripedorangecatglobal-aiwn872djc"          # ← IMPORTANT
EXCHANGE_HOST = "159.65.173.202"             # ← correct host

async def main():
    # Create client
    client = ExchangeClient(
        team_token=TEAM_TOKEN,
        gateway=GatewayConfig(host=EXCHANGE_HOST),
        market_data=MarketDataConfig(host=EXCHANGE_HOST)
    )

    print("Connecting...")
    await client.connect()
    print("Connected!")

    # ---- TEST BUY ORDER ----
    print("\nSubmitting BUY order for 10 shares of XYZ at $100.00...")
    order_id = await client.send_new_async(
        client_id=1,          # Your tracking ID
        symbol_id=1,          # 1 = XYZ
        side=0,               # 0 = BUY
        price_ticks=10000,    # $100.00
        quantity=10
    )

    print("Order submitted! Exchange order_id:", order_id)

    await client.close()
    print("Closed connection.")

if __name__ == "__main__":
    asyncio.run(main())
'''
