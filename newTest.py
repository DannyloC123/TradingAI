import asyncio
import os
import httpx
import numpy as np
from collections import deque
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

load_dotenv("tokens.env")

EXCHANGE_HOST = os.getenv("MARKET_HOST")
TEAM_TOKEN = os.getenv("TEAM_TOKEN")

# ---------------- SETTINGS ----------------
TARGET_EXPOSURE = 400_000
MAX_TRADE_NOTIONAL = 100_000
REVERSAL_NOTIONAL = 100_000   # <<< OPTION B
AGGRESSIVE = 0.03
LOOP_DELAY = 0

SYMBOLS = {"XYZ": 1, "ABC": 3, "DEF": 4, "ETF": 2}
WEIGHTS = {"XYZ": 0.5, "ABC": 0.3, "DEF": 0.2}

STOP_LOSS = -0.05
TAKE_PROFIT = 0.005

# ---------------- QUOTES ----------------
async def get_quotes(session):
    try:
        r = await session.get(f"http://{EXCHANGE_HOST}:8081/quotes")
        return r.json()
    except:
        return None

# ---------------- EXPOSURE ----------------
class Exposure:
    def __init__(self, client):
        self.client = client
        self.exposure = 0
        self.req_id = 1_000_000

    async def record(self, symbol, qty, price):
        self.exposure += abs(qty * price)

    async def ensure_minimum(self, mid):
        if self.exposure >= TARGET_EXPOSURE:
            return

        deficit = TARGET_EXPOSURE - self.exposure
        qty = int(deficit / mid["ETF"])

        print(f"[EXPOSURE] Buying {qty} ETF to maintain $400k")

        price = mid["ETF"] + AGGRESSIVE
        ticks = int(price * 100)
        self.req_id += 1

        await self.client.send_new_async(
            client_id=self.req_id,
            symbol_id=SYMBOLS["ETF"],
            side=0,
            price_ticks=ticks,
            quantity=qty
        )

        await self.record("ETF", qty, price)

# ---------------- ETF ARBITRAGE (UNCHANGED) ----------------
class ETFArb:
    def __init__(self, client, exposure):
        self.client = client
        self.exposure = exposure
        self.req_id = 300_000

    async def send(self, symbol, side, price, qty):
        adj = price + AGGRESSIVE if side == 0 else price - AGGRESSIVE
        ticks = int(adj * 100)
        self.req_id += 1

        await self.client.send_new_async(
            client_id=self.req_id,
            symbol_id=SYMBOLS[symbol],
            side=side,
            price_ticks=ticks,
            quantity=qty
        )
        await self.exposure.record(symbol, qty, adj)

    async def run_arb(self, q):
        bid, ask = q["ETF"]["bid"], q["ETF"]["ask"]
        mid = (bid + ask) / 2

        basket_buy = sum(WEIGHTS[s] * q[s]["ask"] for s in ["XYZ", "ABC", "DEF"])
        basket_sell = sum(WEIGHTS[s] * q[s]["bid"] for s in ["XYZ", "ABC", "DEF"])

        sell_spread = bid - basket_buy
        buy_spread = basket_sell - ask

        qty = int(MAX_TRADE_NOTIONAL / mid)

        if sell_spread > 0.03:
            print(f"[ETF ARB] SELL ETF spread={sell_spread:.4f}")
            await self.send("ETF", 1, q["ETF"]["bid"], qty)
            await self.send("XYZ", 0, q["XYZ"]["ask"], int(qty * 0.5))
            await self.send("ABC", 0, q["ABC"]["ask"], int(qty * 0.3))
            await self.send("DEF", 0, q["DEF"]["ask"], int(qty * 0.2))

        elif buy_spread > 0.03:
            print(f"[ETF ARB] BUY ETF spread={buy_spread:.4f}")
            await self.send("ETF", 0, q["ETF"]["ask"], qty)
            await self.send("XYZ", 1, q["XYZ"]["bid"], int(qty * 0.5))
            await self.send("ABC", 1, q["ABC"]["bid"], int(qty * 0.3))
            await self.send("DEF", 1, q["DEF"]["bid"], int(qty * 0.2))


# ---------------- STOCK TRADER WITH STOP LOSS + TP ----------------
class StockTrader:
    def __init__(self, client, exposure):
        self.client = client
        self.exposure = exposure
        self.req_id = 500_000

        self.history = {s: deque(maxlen=12) for s in ["XYZ", "ABC", "DEF"]}

        # Track position and entry price
        self.position = {s: 0 for s in ["XYZ", "ABC", "DEF"]}
        self.entry =   {s: None for s in ["XYZ", "ABC", "DEF"]}

    async def send(self, symbol, side, price, qty):
        adj = price + AGGRESSIVE if side == 0 else price - AGGRESSIVE
        ticks = int(adj * 100)
        self.req_id += 1

        await self.client.send_new_async(
            client_id=self.req_id,
            symbol_id=SYMBOLS[symbol],
            side=side,
            price_ticks=ticks,
            quantity=qty
        )
        await self.exposure.record(symbol, qty, adj)

    def unrealized_pnl(self, symbol, mid):
        pos = self.position[symbol]
        if pos == 0 or self.entry[symbol] is None:
            return 0

        if pos > 0:
            return (mid - self.entry[symbol]) / self.entry[symbol]
        else:
            return (self.entry[symbol] - mid) / self.entry[symbol]

    async def reverse_position(self, symbol, mid):
        current_pos = self.position[symbol]
        if current_pos != 0:
            # close position
            side = 1 if current_pos > 0 else 0
            print(f"[CLOSE] Closing {symbol} {current_pos} shares")
            await self.send(symbol, side, mid, abs(current_pos))

        # open reverse with fixed notional
        qty = int(REVERSAL_NOTIONAL / mid)
        new_side = 0 if current_pos < 0 else 1  # buy if previously short
        print(f"[REVERSE] Opening new {symbol} pos, qty={qty}")

        await self.send(symbol, new_side, mid, qty)

        self.position[symbol] = qty if new_side == 0 else -qty
        self.entry[symbol] = mid

    async def trade(self, symbol, q):
        bid = q[symbol]["bid"]
        ask = q[symbol]["ask"]
        if bid is None or ask is None:
            return

        mid = (bid + ask) / 2

        # Update price history
        self.history[symbol].append(mid)

        # ---------------- CHECK STOP LOSS & TAKE PROFIT ----------------
        pnl = self.unrealized_pnl(symbol, mid)

        if pnl <= STOP_LOSS:
            print(f"[STOP LOSS] {symbol} pnl={pnl:.3f}")
            await self.reverse_position(symbol, mid)
            return

        if pnl >= TAKE_PROFIT:
            print(f"[TAKE PROFIT] {symbol} pnl={pnl:.3f}")
            await self.reverse_position(symbol, mid)
            return

        # ---------------- MOMENTUM-BASED ENTRY ----------------
        data = list(self.history[symbol])
        if len(data) < 8:
            return

        slope = np.polyfit(range(5), data[-5:], 1)[0]
        qty = int(60_000 / mid)

        if self.position[symbol] == 0:
            if slope > 0.015:
                print(f"[ENTRY] BUY {symbol} momentum={slope:.3f}")
                await self.send(symbol, 0, ask, qty)
                self.position[symbol] = qty
                self.entry[symbol] = mid
            elif slope < -0.015:
                print(f"[ENTRY] SELL {symbol} momentum={slope:.3f}")
                await self.send(symbol, 1, bid, qty)
                self.position[symbol] = -qty
                self.entry[symbol] = mid


# ---------------- MAIN LOOP ----------------
async def main():
    client = ExchangeClient(
        team_token=TEAM_TOKEN,
        gateway=GatewayConfig(host=EXCHANGE_HOST),
        market_data=MarketDataConfig(host=EXCHANGE_HOST)
    )
    await client.connect()
    print("CONNECTED.")

    

    session = httpx.AsyncClient()
    exposure = Exposure(client)
    etf = ETFArb(client, exposure)
    stock = StockTrader(client, exposure)

    

    while True:
        q = await get_quotes(session)
        if not q:
            continue

        mids = {s: (q[s]["bid"] + q[s]["ask"]) / 2 for s in SYMBOLS if q[s]["bid"]}

        await exposure.ensure_minimum(mids)
        await etf.run_arb(q)

        for s in ["XYZ", "ABC", "DEF"]:
            await stock.trade(s, q)

        await asyncio.sleep(LOOP_DELAY)

if __name__ == "__main__":
    asyncio.run(main())
