import asyncio
import os
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig
import httpx
import asyncio
import numpy as np
import collections

# Load token from tokens.env
load_dotenv("tokens.env")

# --- GLOBAL SETTINGS (Absolute Max Profit Configuration) ---
EXCHANGE_HOST = os.getenv("MARKET_HOST") # Use env var for robustness
MAX_TRADE_NOTIONAL = 1000000             # $1M Notional
MIN_PROFIT_THRESHOLD = 0.03              # Aggressively low for MAX frequency
AGGRESSIVE_MARKET_PRICE = 0.05           # Ensures instant fill

# ---------------- TRADING FUNCTIONS (REMOVED) -----------------
# The global 'buy' and 'sell' functions, and the SymbolWrapper class are removed 
# to eliminate latency. Order submission is now handled directly inside OptimisedArbBot.

# --- Global Data Fetching (Kept for MeanReversionBot and Market Analysis) ---
# Note: get_all_prices is used by the OptimisedArbBot for max speed.

async def get_bid_ask(symbol):
    """Fetches bid/ask for a single symbol with retries."""
    async with httpx.AsyncClient(timeout=1.0) as client: 
        for _ in range(5): 
            try:
                r = await client.get(f"http://{EXCHANGE_HOST}:8081/quotes")
                data = r.json()
                bid = data[symbol]["bid"]
                ask = data[symbol]["ask"]
                return bid, ask
            except Exception:
                await asyncio.sleep(0.01)
    return None, None

# ---------------- SYMBOL CLASSES (Simplified) -----------------

class SymbolData:
    """Simple container for symbol data used by the bots."""
    def __init__(self, ticker, symbolID):
        self.ticker = ticker
        self.symbolID = symbolID

ETF = SymbolData("ETF", 2)
XYZ = SymbolData("XYZ", 1)
ABC = SymbolData("ABC", 3)
DEF = SymbolData("DEF", 4)


# ---------------- STRATEGY IMPLEMENTATION -----------------

## 🐢 Mean Reversion Bot (Trading Component Stocks: ABC, DEF, XYZ)
class MeanReversionBot:
    """Trades a single component stock based on mean reversion logic."""
    def __init__(self, client, symbol_obj):
        self.client = client
        self.symbol = symbol_obj

        self.history_len = 20
        self.price_history = collections.deque(maxlen=self.history_len)
        self.max_pos_dollars = 100000
        self.small_pos_pct = 0.30
        self.current_tier = 0
        self.side = None
        self.client_req_id = 1000 # Separate ID block for MR Bot

    async def _send_order(self, side, price, qty):
        """MR Bot's direct order submission (no aggressive offset needed for MR)."""
        if qty <= 0: return
        self.client_req_id += 1
        price_ticks = int(price * 100) # Use market price without aggressive offset
        
        try:
            await self.client.send_new_async(
                client_id=self.client_req_id,
                symbol_id=self.symbol.symbolID,
                side=side,
                price_ticks=price_ticks,
                quantity=qty
            )
            print(f"[MR {self.symbol.ticker}] {'BUY' if side == 0 else 'SELL'} @ ${price:.2f} x{qty}")
        except Exception:
            pass

    async def run(self):
        print(f"--- Starting Mean Reversion Bot for {self.symbol.ticker} ---")
        while True:
            bid, ask = await get_bid_ask(self.symbol.ticker)
            
            if bid is None or ask is None:
                await asyncio.sleep(1); continue
            
            current_price = (bid + ask) / 2
            self.price_history.append(current_price)
            
            if len(self.price_history) < self.history_len:
                await asyncio.sleep(1); continue
            
            avg_price = np.mean(self.price_history)
            deviation = current_price - avg_price

            # --- Mean Reversion Logic (remains the same) ---
            if deviation >= 0.80:
                if self.current_tier != 2 or self.side != 'SHORT':
                    qty = int(self.max_pos_dollars / current_price)
                    await self._send_order(1, bid, qty)
                    self.current_tier = 2; self.side = 'SHORT'
            elif deviation >= 0.30:
                if self.current_tier == 0:
                    qty = int((self.max_pos_dollars * self.small_pos_pct) / current_price)
                    await self._send_order(1, bid, qty)
                    self.current_tier = 1; self.side = 'SHORT'
            elif deviation <= -0.80:
                if self.current_tier != 2 or self.side != 'LONG':
                    qty = int(self.max_pos_dollars / current_price)
                    await self._send_order(0, ask, qty)
                    self.current_tier = 2; self.side = 'LONG'
            elif deviation <= -0.30:
                if self.current_tier == 0:
                    qty = int((self.max_pos_dollars * self.small_pos_pct) / current_price)
                    await self._send_order(0, ask, qty)
                    self.current_tier = 1; self.side = 'LONG'

            await asyncio.sleep(1) # MR can afford to wait 1 second

## 🚀 Optimised Arbitrage Bot (Trading ETF & Basket)
class OptimisedArbBot:
    """Executes the 4-legged ETF Arbitrage at max speed and volume."""
    def __init__(self, client):
        self.client = client
        self.http_client = httpx.AsyncClient() 
        self.req_id = 1000000 # High client ID block for HFT
        
        self.weights = {'XYZ': 0.5, 'ABC': 0.3, 'DEF': 0.2}
        self.sym_ids = {'XYZ': 1, 'ETF': 2, 'ABC': 3, 'DEF': 4}

    async def get_all_prices(self):
        """Fetches all quotes in a single request for speed."""
        try:
            r = await self.http_client.get(f"http://{EXCHANGE_HOST}:8081/quotes")
            return r.json()
        except Exception:
            return None

    async def _send_order_raw(self, ticker, side, price, qty):
        """Sends a zero-latency, aggressive order directly to the client."""
        if qty <= 0: return
        self.req_id += 1
        
        # Aggression Logic (CRITICAL for instant fill)
        price_aggressed = price + AGGRESSIVE_MARKET_PRICE if side == 0 else price - AGGRESSIVE_MARKET_PRICE
        price_ticks = int(price_aggressed * 100)
        
        try:
            await self.client.send_new_async(
                client_id=self.req_id,
                symbol_id=self.sym_ids[ticker],
                side=side,
                price_ticks=price_ticks,
                quantity=qty
            )
            # Minimal log for debugging, but must be fast
            # print(f"[{'BUY' if side == 0 else 'SELL'}] {ticker} @ ${price_aggressed:.2f} x{qty}")
        except Exception:
            pass

    async def execute_basket(self, side, qty_etf, prices):
        """Executes all 4 legs SIMULTANEOUSLY using the raw sender."""
        tasks = []
        
        qty_xyz = int(qty_etf * self.weights['XYZ'])
        qty_abc = int(qty_etf * self.weights['ABC'])
        qty_def = int(qty_etf * self.weights['DEF'])
        
        if side == 'SELL_ETF':
            # Sell ETF (Bid) + Buy Components (Ask)
            # print(f">>> ARB EXECUTION: Sell {qty_etf} ETF | Buy Components")
            tasks.append(self._send_order_raw("ETF", 1, prices['ETF']['bid'], qty_etf))
            tasks.append(self._send_order_raw("XYZ", 0, prices['XYZ']['ask'], qty_xyz))
            tasks.append(self._send_order_raw("ABC", 0, prices['ABC']['ask'], qty_abc))
            tasks.append(self._send_order_raw("DEF", 0, prices['DEF']['ask'], qty_def))
            
        elif side == 'BUY_ETF':
            # Buy ETF (Ask) + Sell Components (Bid)
            # print(f">>> ARB EXECUTION: Buy {qty_etf} ETF | Sell Components")
            tasks.append(self._send_order_raw("ETF", 0, prices['ETF']['ask'], qty_etf))
            tasks.append(self._send_order_raw("XYZ", 1, prices['XYZ']['bid'], qty_xyz))
            tasks.append(self._send_order_raw("ABC", 1, prices['ABC']['bid'], qty_abc))
            tasks.append(self._send_order_raw("DEF", 1, prices['DEF']['bid'], qty_def))

        # CRITICAL: Concurrent submission to lock in the spread 
        await asyncio.gather(*tasks) 

    async def run(self):
        print(f"--- STARTING MAX PROFIT ARBITRAGE (Threshold: ${MIN_PROFIT_THRESHOLD:.2f}, Notional: ${MAX_TRADE_NOTIONAL}) ---")
        while True:
            quotes = await self.get_all_prices()
            if not quotes or not all(k in quotes for k in ['XYZ', 'ABC', 'DEF', 'ETF']):
                await asyncio.sleep(0.001); continue

            # True Profit Calculation (Uses Bids/Asks)
            cost_buy_basket = (
                self.weights['XYZ'] * quotes['XYZ']['ask'] + 
                self.weights['ABC'] * quotes['ABC']['ask'] + 
                self.weights['DEF'] * quotes['DEF']['ask']
            )
            proceeds_sell_basket = (
                self.weights['XYZ'] * quotes['XYZ']['bid'] + 
                self.weights['ABC'] * quotes['ABC']['bid'] + 
                self.weights['DEF'] * quotes['DEF']['bid']
            )

            bid_etf = quotes['ETF']['bid']
            ask_etf = quotes['ETF']['ask']

            # Spread A: Sell ETF, Buy Basket (ETF is overpriced)
            spread_sell_etf = bid_etf - cost_buy_basket
            
            # Spread B: Buy ETF, Sell Basket (ETF is underpriced)
            spread_buy_etf = proceeds_sell_basket - ask_etf

            # Execution Logic
            current_etf_price = (bid_etf + ask_etf) / 2
            target_qty = int(MAX_TRADE_NOTIONAL / current_etf_price)
            
            if spread_sell_etf > MIN_PROFIT_THRESHOLD:
                # print(f"[ARB FOUND] SELL: Spread: {spread_sell_etf:.2f}. Executing {target_qty}...")
                await self.execute_basket('SELL_ETF', target_qty, quotes)
                # REMOVED: await asyncio.sleep(0.05) 
                
            elif spread_buy_etf > MIN_PROFIT_THRESHOLD:
                # print(f"[ARB FOUND] BUY: Spread: {spread_buy_etf:.2f}. Executing {target_qty}...")
                await self.execute_basket('BUY_ETF', target_qty, quotes)
                # REMOVED: await asyncio.sleep(0.05) 
            
            await asyncio.sleep(0.001) # Tightest possible loop for scanning

## 🚫 Simple ETF Arbitrage Bot (Discarded/Not Used)
# The ETFArbitrageBot class is left out as the OptimisedArbBot is superior.

# -------------- MAIN PROGRAM ----------------------

async def main():
    team_token = os.getenv("TEAM_TOKEN")
    
    # Check if the exchange host is available in environment variables
    if not EXCHANGE_HOST:
        print("ERROR: MARKET_HOST environment variable not set.")
        return

    client = ExchangeClient(
        team_token=team_token,
        gateway=GatewayConfig(host=EXCHANGE_HOST),
        market_data=MarketDataConfig(host=EXCHANGE_HOST)
    )

    try:
        await client.connect()
        print("Connected successfully!")

        # 💥 STARTING MAX PROFIT BOTS CONCURRENTLY 💥
        
        # 1. High-Speed ETF Arbitrage Bot (Trades all 4 symbols)
        arb_bot = OptimisedArbBot(client)
        
        # 2. Mean Reversion Bots (Trades component stocks only)
        # Note: You can choose to run one or all of these concurrently with the Arb bot.
        mr_bots = [
            MeanReversionBot(client, XYZ),
            MeanReversionBot(client, ABC),
            MeanReversionBot(client, DEF),
        ]

        # Run all active bots simultaneously
        tasks = [
            arb_bot.run(),
            mr_bots[0].run(),
            mr_bots[1].run(),
            mr_bots[2].run(),
        ]

        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        await client.close()
        print("Client closed.")

if __name__ == "__main__":
    asyncio.run(main())