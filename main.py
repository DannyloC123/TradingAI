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


class ETFArbitrageBot:
    def __init__(self, client):
        self.client = client
        self.tickers = {"XYZ": 0.5, "ABC": 0.3, "DEF": 0.2} 
        
        # Define IDs explicitly here to replace the missing symbol objects
        # This mapping assumes your external 'sell' and 'buy' helpers require the integer ID
        self.ids = {'XYZ': 1, 'ETF': 2, 'ABC': 3, 'DEF': 4} 
        
        # --- OPTIMAL SETTINGS (Keep these) ---
        self.threshold_small = 0.07 
        self.threshold_large = 0.15 
        self.small_qty = 200      
        self.large_qty = 1000     
        self.req_id = 50000

    # missing run
    

    async def execute_sell_arb(self, qty, quotes):
        """Sell ETF (primary) and Buy Basket (hedge) CONCURRENTLY."""
        tasks = []
        
        # 1. Sell ETF (Primary Leg) - Use ID self.ids["ETF"]
        tasks.append(sell(self.client, self.ids["ETF"], quotes["ETF"][0], qty, self.req_id)); self.req_id += 1

        # 2. Buy Basket (Hedge Legs) - Use IDs
        tasks.append(buy(self.client, self.ids["XYZ"], quotes["XYZ"][1], int(qty*0.5), self.req_id)); self.req_id += 1
        tasks.append(buy(self.client, self.ids["ABC"], quotes["ABC"][1], int(qty*0.3), self.req_id)); self.req_id += 1
        tasks.append(buy(self.client, self.ids["DEF"], quotes["DEF"][1], int(qty*0.2), self.req_id)); self.req_id += 1
        
        # Execute all 4 orders at the same time
        await asyncio.gather(*tasks)

    async def execute_buy_arb(self, qty, quotes):
        """Buy ETF (primary) and Sell Basket (hedge) CONCURRENTLY."""
        tasks = []
        
        # 1. Buy ETF (Primary Leg) - Use ID self.ids["ETF"]
        tasks.append(buy(self.client, self.ids["ETF"], quotes["ETF"][1], qty, self.req_id)); self.req_id += 1

        # 2. Sell Basket (Hedge Legs) - Use IDs
        tasks.append(sell(self.client, self.ids["XYZ"], quotes["XYZ"][0], int(qty*0.5), self.req_id)); self.req_id += 1
        tasks.append(sell(self.client, self.ids["ABC"], quotes["ABC"][0], int(qty*0.3), self.req_id)); self.req_id += 1
        tasks.append(sell(self.client, self.ids["DEF"], quotes["DEF"][0], int(qty*0.2), self.req_id)); self.req_id += 1
        
        # Execute all 4 orders at the same time
        await asyncio.gather(*tasks)


# --- GLOBAL SETTINGS (Update these values) ---
EXCHANGE_HOST = "159.65.173.202"
MAX_TRADE_NOTIONAL = 250000 
MIN_PROFIT_THRESHOLD = 0.08  # <--- CRITICAL FIX: Higher threshold to absorb slippage
AGGRESSIVE_MARKET_PRICE = 0.05 # Aggression amount if Market Order isn't supported

# ---------------- OPTIMISED ARBITRAGE BOT (MAX RELIABILITY) -----------------
class OptimisedArbBot:
    def __init__(self, client):
        self.client = client
        self.http_client = httpx.AsyncClient() 
        self.req_id = 100000
        
        self.weights = {'XYZ': 0.5, 'ABC': 0.3, 'DEF': 0.2}
        self.sym_ids = {'XYZ': 1, 'ETF': 2, 'ABC': 3, 'DEF': 4}

    # async def get_all_prices(self): ... (KEEP THIS METHOD) ...
    # Insert this method inside the class OptimisedArbBot:

    async def get_all_prices(self):
        """Fetches all quotes in a single request or parallel requests"""
        try:
            # Most efficient: fetch the full quote map once
            r = await self.http_client.get(f"http://{EXCHANGE_HOST}:8081/quotes")
            return r.json()
        except Exception as e:
            # Print the error for debugging, then return None
            # print(f"[Data Error] {e}") # This line is usually in the run loop, but good to keep.
            return None

    async def execute_basket(self, side, qty_etf, prices):
        """Executes all 4 legs SIMULTANEOUSLY using highly aggressive prices."""
        tasks = []
        
        qty_xyz = int(qty_etf * 0.5)
        qty_abc = int(qty_etf * 0.3)
        qty_def = int(qty_etf * 0.2)
        
        if side == 'SELL_ETF':
            # Sell ETF, Buy Components
            print(f">>> HARD EXECUTION: Sell {qty_etf} ETF | Buy Components")
            # All orders sent aggressively past the current best price to ensure a fill
            tasks.append(self.send_order("ETF", 1, prices['ETF']['bid'], qty_etf))
            tasks.append(self.send_order("XYZ", 0, prices['XYZ']['ask'], qty_xyz))
            tasks.append(self.send_order("ABC", 0, prices['ABC']['ask'], qty_abc))
            tasks.append(self.send_order("DEF", 0, prices['DEF']['ask'], qty_def))
            
        elif side == 'BUY_ETF':
            # Buy ETF, Sell Components
            print(f">>> HARD EXECUTION: Buy {qty_etf} ETF | Sell Components")
            tasks.append(self.send_order("ETF", 0, prices['ETF']['ask'], qty_etf))
            tasks.append(self.send_order("XYZ", 1, prices['XYZ']['bid'], qty_xyz))
            tasks.append(self.send_order("ABC", 1, prices['ABC']['bid'], qty_abc))
            tasks.append(self.send_order("DEF", 1, prices['DEF']['bid'], qty_def))

        await asyncio.gather(*tasks)

    async def send_order(self, ticker, side, price, qty):
        """
        CRITICAL FIX: Uses a highly aggressive price (e.g., 5 cents through the book) 
        to guarantee an immediate fill, prioritizing hedging over price perfection.
        """
        if qty <= 0: return
        try:
            self.req_id += 1
            
            # --- AGGRESSION LOGIC ---
            # If Buying (side=0), the price must be higher than the Ask.
            # If Selling (side=1), the price must be lower than the Bid.
            
            # We use the current best price + 5 cents of aggression
            price_aggressed = price + AGGRESSIVE_MARKET_PRICE if side == 0 else price - AGGRESSIVE_MARKET_PRICE
            price_ticks = int(price_aggressed * 100)
            
            await self.client.send_new_async(
                client_id=self.req_id,
                symbol_id=self.sym_ids[ticker],
                side=side,
                price_ticks=price_ticks,
                quantity=qty
            )
        except Exception as e:
            print(f"[Order Error] {ticker}: {e}")

    async def run(self):
        print("--- STARTING MAX RELIABILITY ARBITRAGE (Threshold: $0.25) ---")
        while True:
            # 1. Get Data (using your existing fast get_all_prices method)
            quotes = await self.get_all_prices()
            if not quotes or not all(k in quotes for k in ['XYZ', 'ABC', 'DEF', 'ETF']):
                await asyncio.sleep(0.1); continue

            # 2. Calculate True Profit Margins
            cost_buy_basket = (0.5 * quotes['XYZ']['ask'] + 0.3 * quotes['ABC']['ask'] + 0.2 * quotes['DEF']['ask'])
            proceeds_sell_basket = (0.5 * quotes['XYZ']['bid'] + 0.3 * quotes['ABC']['bid'] + 0.2 * quotes['DEF']['bid'])

            bid_etf = quotes['ETF']['bid']
            ask_etf = quotes['ETF']['ask']

            # Opportunity A: ETF is expensive. Sell ETF (at Bid), Buy Basket (at Ask).
            spread_sell_etf = bid_etf - cost_buy_basket
            
            # Opportunity B: ETF is cheap. Buy ETF (at Ask), Sell Basket (at Bid).
            spread_buy_etf = proceeds_sell_basket - ask_etf

            # 3. Execution Logic
            current_etf_price = (bid_etf + ask_etf) / 2
            
            target_qty = int(MAX_TRADE_NOTIONAL / current_etf_price)
            
            if spread_sell_etf > MIN_PROFIT_THRESHOLD:
                print(f"[ARB FOUND] SELL: Spread: {spread_sell_etf:.2f}. Executing {target_qty}...")
                await self.execute_basket('SELL_ETF', target_qty, quotes)
                await asyncio.sleep(0.5) 
                
            elif spread_buy_etf > MIN_PROFIT_THRESHOLD:
                print(f"[ARB FOUND] BUY: Spread: {spread_buy_etf:.2f}. Executing {target_qty}...")
                await self.execute_basket('BUY_ETF', target_qty, quotes)
                await asyncio.sleep(0.5)
            
            else:
                await asyncio.sleep(0.05) # Keep the loop tight

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
    #bot_xyz = MeanReversionBot(client, XYZ())
    #bot_etf = MeanReversionBot(client, ETF())
    #bot_abc = MeanReversionBot(client, ABC())
    #bot_def = MeanReversionBot(client, DEF())

    bot = OptimisedArbBot(client)
    await bot.run()

    # Run all at the same time
    #await asyncio.gather(
        #bot_xyz.run(),
        #bot_etf.run(),
        #bot_abc.run(),
        #bot_def.run()
    #)
    # Example trades:
    #order1 = await buy(client, XYZ, price_dollars=0, quantity=200, client_id=1)
    #print("BUY order sent:", order1)

    #order2 = await sell(client, ABC, price_dollars=50.25, quantity=5, client_id=2)
    #print("SELL order sent:", order2)

    await client.close()

asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())




'''
import asyncio
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

TEAM_TOKEN = "TEAM_TOKEN"          # ← IMPORTANT
EXCHANGE_HOST = "MARKET_HOST"             # ← correct host

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
