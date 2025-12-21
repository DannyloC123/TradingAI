import asyncio
import os
import httpx
import numpy as np
from dotenv import load_dotenv
from exchange_sdk import ExchangeClient
from exchange_sdk.client import GatewayConfig, MarketDataConfig

load_dotenv("tokens.env")

EXCHANGE_HOST = os.getenv("MARKET_HOST")
TEAM_TOKEN = os.getenv("TEAM_TOKEN")

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
TARGET_EXPOSURE = 400_000       # ALWAYS maintain at least this much
AGGRESSIVE = 0.05               # price offset to guarantee fill
MEAN_WINDOW = 20
MIN_SPREAD = 0.03
MAX_TRADE_NOTIONAL = 100_000    # per arbitrage cycle
LOOP_DELAY = 0                  # fastest possible loop

# Symbol IDs
SYMBOLS = {
    "XYZ": 1,
    "ETF": 2,
    "ABC": 3,
    "DEF": 4
}

WEIGHTS = {"XYZ": 0.5, "ABC": 0.3, "DEF": 0.2}

# ---------------------------------------------------------
# SHARED PRICE FETCHER
# ---------------------------------------------------------
async def get_quotes(client):
    try:
        r = await client.get(f"http://{EXCHANGE_HOST}:8081/quotes")
        return r.json()
    except:
        return None

# ---------------------------------------------------------
# GLOBAL EXPOSURE MANAGER
# ---------------------------------------------------------
class ExposureManager:
    def __init__(self, client):
        self.client = client
        self.exposure = 0
        self.req_id = 10_000_000

    async def update_exposure(self, quotes):
        """Estimate portfolio exposure using mid-prices."""
        mids = {
            s: (quotes[s]["bid"] + quotes[s]["ask"]) / 2
            for s in SYMBOLS.keys()
        }
        # No position tracking API → assume exposure approx. = total traded value
        # We'll update exposure when placing trades
        return mids

    async def force_exposure(self, mids):
        """If exposure < TARGET_EXPOSURE, open ETF until target reached."""
        deficit = TARGET_EXPOSURE - self.exposure
        if deficit <= 0:
            return

        qty = int(deficit / mids["ETF"])
        if qty <= 0:
            return

        print(f"\n[FORCE EXPOSURE] Buying {qty} ETF to restore exposure.")

        self.req_id += 1
        price_ticks = int((mids["ETF"] + AGGRESSIVE) * 100)

        await self.client.send_new_async(
            client_id=self.req_id,
            symbol_id=SYMBOLS["ETF"],
            side=0,
            price_ticks=price_ticks,
            quantity=qty
        )

        self.exposure += qty * mids["ETF"]

    async def register_trade(self, value):
        """Increase exposure whenever a trade is executed."""
        self.exposure += abs(value)

# ---------------------------------------------------------
# MEAN REVERSION ENGINE
# ---------------------------------------------------------
class MeanReversion:
    def __init__(self):
        self.history = {s: [] for s in ["XYZ", "ABC", "DEF"]}

    def update(self, symbol, price):
        hist = self.history[symbol]
        hist.append(price)
        if len(hist) > MEAN_WINDOW:
            hist.pop(0)

        if len(hist) < MEAN_WINDOW:
            return None

        avg = sum(hist) / len(hist)
        dev = price - avg
        return dev

# ---------------------------------------------------------
# ARBITRAGE ENGINE
# ---------------------------------------------------------
class Arbitrage:
    def __init__(self, client, exposure_mgr):
        self.client = client
        self.exposure_mgr = exposure_mgr
        self.req_id = 300_000

    async def send(self, ticker, side, price, qty):
        if qty <= 0:
            return

        price_adj = price + AGGRESSIVE if side == 0 else price - AGGRESSIVE
        ticks = int(price_adj * 100)
        self.req_id += 1

        await self.client.send_new_async(
            client_id=self.req_id,
            symbol_id=SYMBOLS[ticker],
            side=side,
            price_ticks=ticks,
            quantity=qty
        )

        mid = price
        await self.exposure_mgr.register_trade(qty * mid)

    async def arb(self, quotes):
        bidETF = quotes["ETF"]["bid"]
        askETF = quotes["ETF"]["ask"]

        # Basket values
        buy_basket = (
            WEIGHTS["XYZ"] * quotes["XYZ"]["ask"] +
            WEIGHTS["ABC"] * quotes["ABC"]["ask"] +
            WEIGHTS["DEF"] * quotes["DEF"]["ask"]
        )

        sell_basket = (
            WEIGHTS["XYZ"] * quotes["XYZ"]["bid"] +
            WEIGHTS["ABC"] * quotes["ABC"]["bid"] +
            WEIGHTS["DEF"] * quotes["DEF"]["bid"]
        )

        spread_sell = bidETF - buy_basket
        spread_buy = sell_basket - askETF

        mid = (bidETF + askETF) / 2
        qty = int(MAX_TRADE_NOTIONAL / mid)

        if spread_sell > MIN_SPREAD:
            print(f"[ARB] SELL ETF spread={spread_sell:.3f}")
            await self.send("ETF", 1, bidETF, qty)
            await self.send("XYZ", 0, quotes["XYZ"]["ask"], int(qty * 0.5))
            await self.send("ABC", 0, quotes["ABC"]["ask"], int(qty * 0.3))
            await self.send("DEF", 0, quotes["DEF"]["ask"], int(qty * 0.2))

        elif spread_buy > MIN_SPREAD:
            print(f"[ARB] BUY ETF spread={spread_buy:.3f}")
            await self.send("ETF", 0, askETF, qty)
            await self.send("XYZ", 1, quotes["XYZ"]["bid"], int(qty * 0.5))
            await self.send("ABC", 1, quotes["ABC"]["bid"], int(qty * 0.3))
            await self.send("DEF", 1, quotes["DEF"]["bid"], int(qty * 0.2))

# ---------------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------------
async def main():
    client = ExchangeClient(
        team_token=TEAM_TOKEN,
        gateway=GatewayConfig(host=EXCHANGE_HOST),
        market_data=MarketDataConfig(host=EXCHANGE_HOST)
    )
    await client.connect()
    print("CONNECTED.")

    http_client = httpx.AsyncClient()

    exposure_mgr = ExposureManager(client)
    arb = Arbitrage(client, exposure_mgr)
    mr = MeanReversion()

    while True:
        quotes = await get_quotes(http_client)
        if not quotes:
            continue

        # Update exposure using mid-prices
        mids = await exposure_mgr.update_exposure(quotes)

        # FORCE minimum exposure
        await exposure_mgr.force_exposure(mids)

        # Mean reversion signals
        for sym in ["XYZ", "ABC", "DEF"]:
            dev = mr.update(sym, mids[sym])
            if dev is None:
                continue

            if dev > 0.60:  # SHORT
                qty = int(50_000 / mids[sym])
                print(f"[MR] SHORT {sym}")
                await arb.send(sym, 1, quotes[sym]["bid"], qty)

            elif dev < -0.60:  # LONG
                qty = int(50_000 / mids[sym])
                print(f"[MR] LONG {sym}")
                await arb.send(sym, 0, quotes[sym]["ask"], qty)

        # ETF arbitrage
        await arb.arb(quotes)

        await asyncio.sleep(LOOP_DELAY)

if __name__ == "__main__":
    asyncio.run(main())
