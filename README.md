# Algorithmic Trading Competition — Notre Dame DELTA

## Overview

This project documents my team’s participation in **Notre Dame DELTA’s Algorithmic Trading Competition**, where we designed and deployed fully automated trading algorithms in a live, simulated financial market.

The objective was to **maximize net profit (P&L)** while managing volatility, transaction costs, and strict exchange risk limits.

**Final Placement:** 7th out of 14 teams.

---

## Team

**Team Name:** *The Striped Orange Cat Global*

---

## Market & Instruments

- Traded four instruments: **XYZ, ABC, DEF (stocks)** and **ETF (basket fund)**
- ETF represented a weighted basket:
  - 50% XYZ  
  - 30% ABC  
  - 20% DEF  
- Prices updated in real time with realistic volatility and jump dynamics

---

## Strategies Implemented

### Mean Reversion
- Tracked rolling mid-price averages using short moving windows
- Entered tiered long/short positions based on deviation thresholds
- Scaled exposure dynamically using dollar-based position sizing
- Designed to perform during price overreaction and volatility spikes

### ETF Arbitrage
- Continuously computed ETF fair value from underlying basket prices
- Detected mispricing opportunities above transaction cost thresholds
- Executed all hedge legs **concurrently** to minimize execution risk
- Prioritized hedge completion and exposure neutrality over price perfection

---

## Risk Management & Constraints

- Enforced notional exposure caps per trade
- Respected exchange position limits and gross exposure limits
- Accounted for maker/taker fees and slippage
- Avoided rate-limit and cancel-ratio violations
- Used aggressive pricing only when necessary to guarantee hedge fills

---

## Technical Summary

This system was built as a **fully asynchronous, event-driven trading framework** designed for low-latency decision making and reliable execution under strict exchange constraints.

Key technical components include:

- **Asynchronous architecture (async/await):**  
  Enabled concurrent market data ingestion, signal evaluation, and multi-leg order execution without blocking.

- **Modular strategy design:**  
  Independent strategy bots (mean reversion and ETF arbitrage) with isolated logic, state tracking, and execution paths.

- **Real-time market data processing:**  
  Pulled live quotes, order book data, and recent trades via REST APIs with retry handling and timeout control.

- **Statistical signal generation:**  
  Used rolling averages, deviation thresholds, and basket valuation math to identify trade opportunities.

- **Concurrent hedge execution:**  
  ETF arbitrage trades executed all four legs simultaneously to reduce leg risk and directional exposure.

- **Execution reliability focus:**  
  Aggressive pricing logic ensured rapid fills when hedging was critical, trading price optimality for risk reduction.

- **State and exposure management:**  
  Tracked position tiers, trade sizing, and request IDs to maintain consistency and avoid invalid order operations.

This project closely mirrors real-world algorithmic trading systems, emphasizing **robust execution, risk control, and market microstructure awareness** rather than purely theoretical strategy design.

---

## Skills Demonstrated

- Algorithmic trading strategy design
- Asynchronous Python systems
- Market microstructure & ETF mechanics
- Risk and exposure management
- Real-time data processing
- Multi-leg trade execution
- Performance evaluation under competition constraints