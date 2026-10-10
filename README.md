# Adongo Trading Kit (ATK)

The **Adongo Trading Kit (ATK)** is an advanced, fully automated algorithmic trading application designed for MetaTrader 5 (MT5). 

ATK was primarily built to **test AI agent models** and evaluate algorithmic market analysis in live environments. It serves as a steep learning curve and development milestone for its builder, **[Adongo](https://adongo.me)**. While it is a **production-ready 100% functional trading system**, it must be tested well before deployment on a live real-money account.

## 🧠 The "Brain": How ATK Works

ATK completely automates the trading lifecycle—from analyzing the chart to calculating the financial risk, and finally managing the open position.

### 1. Automated Market Analysis (The Eyes)
ATK constantly watches the markets in real-time. It analyzes the price action, looking for specific setups:
- **Trend Alignment**: Uses a 50-period Moving Average (MA50) to determine the macroeconomic trend. It will only look for Bullish (Buy) setups if the price is above the MA50, and Bearish (Sell) setups if the price is below.
- **Momentum & Candlestick Confirmation**: Uses the Relative Strength Index (RSI) to find the "sweet spot" of momentum. It avoids entering when the market is overbought or oversold.
- **Session Intelligence**: It knows when trading volume is highest (e.g., London and New York overlaps) and weights its trade probabilities accordingly.

### 2. Smart Risk Management (Using Your Real Funds)
ATK does **not** use a hardcoded, blind lot size. Instead, it looks directly at the real funds available in your connected MT5 account.
- It calculates exactly **1% risk** of your current account balance. 
- Based on the distance to the Stop Loss, it mathematically scales the position size. This means whether you have $100 or $10,000 in your account, the bot dynamically adapts its trade size to protect your capital.

### 3. Automatic TP/SL & Loss Minimization
Losses are an inevitable part of trading, but ATK's primary goal is to minimize them.
- **Strict Stop Losses (SL)**: A trade is *never* entered without a hard Stop Loss sent directly to the broker. If the market suddenly reverses, the trade is cut immediately to preserve capital.
- **Layered Take Profits (TP)**: The bot calculates a dynamic Take Profit target based on Risk-to-Reward (RR) multiples (1.5x, 2.5x, 3.5x). It books profits automatically when the market moves in your favor.

### 4. Real Broker Execution & History
ATK sends API commands directly to your local MetaTrader 5 terminal. All trades, whether they are won or lost, are recorded directly into your MT5 Broker Account History, meaning you can verify your performance inside the standard MT5 mobile app or desktop terminal.

---

## 🚀 Getting Started

### 1. Requirements
- **MetaTrader 5**: Ensure the MT5 terminal is installed on your Windows machine and logged into a Demo or Real account.
- **Python 3.9+**: Required to run the bot engine.

### 2. Setup
1. Open a terminal in this folder and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Launching the ATK Dashboard
To start trading and view the live bot operations, launch the Controller Dashboard:

1. Double-click the **`START_CONTROLLER.bat`** file.
2. Your browser will open the Web UI at **`http://localhost:8501`**.
3. **Configure Servers**: Enter your MT5 Login and Password. Select your broker server from the dropdown (e.g., `Exness-Real`, `MetaQuotes-Demo`, or type a custom one).
4. **Connect & Test**: Click "Fetch Live Account Data" to ensure ATK can see your real funds.
5. **Start Trading**: Click **Start Trading**. 

The dashboard provides a **Live Analysis Preview**, allowing you to see the exact chart, candlesticks, and indicator codes ATK is analyzing right before it takes a trade.

---

## ❓ Frequently Asked Questions & Real-World Trading Rules

**Q: How does ATK handle Latency and Slippage during news events?**
A: Network lag between Python and MetaTrader can cause slippage, especially during high-volatility news events like NFP or CPI. ATK uses a rigid `deviation` (Max Slippage) parameter which can be customized in the UI. If the slippage exceeds this tolerance, the trade is instantly rejected. 

**Q: What happens if my internet drops or Windows updates mid-trade? (Orphaned States)**
A: ATK uses **atomic execution**. It never opens a "naked" market order and tries to add a Stop Loss later. The Entry, Take Profit, and Stop Loss are sent in a single, unified ticket to your broker. If your computer catches fire 1 millisecond after the trade is placed, your account is still completely protected by the broker-side Stop Loss.

**Q: How does the bot handle Regime Changes (Sideways/Choppy Markets)?**
A: Trend-following indicators like the MA50 can get whipsawed in flat, low-liquidity markets (like the Asian session). ATK uses a **Session Intelligence** filter to weight or block trades during these off-hours. Future open-source updates will introduce ATR (Average True Range) volatility stop-guards to detect and avoid consolidating markets entirely.

**Q: Isn't a 1% Risk Rule dangerous during Compounding Drawdowns?**
A: Risking a static 1% of your *current* balance means that if you suffer a 6-trade losing streak, your position sizes shrink. While this mathematically protects you from blowing your account, it makes recovering slower (as you are trading with smaller lots). Users can tune their Risk Percentage in the UI Settings to match their risk appetite and recovery strategy.

**Q: Are there Broker Execution Quirks I should worry about?**
A: Yes. Different brokers (Exness vs. MetaQuotes) have different minimum lot steps, slippage rules, and spreads. A strategy that is highly profitable on a zero-spread Demo account can suffer on a Real account due to commission costs. ATK calculates lot sizes rounding to the broker's specific `volume_step`, but you should **always test on your broker's specific Demo server** first to evaluate spread behavior.

**Q: Can my account be banned for using a bot?**
A: No. ATK uses the official, broker-supported `MetaTrader5` Python API. It does not use latency-arbitrage hacks or illegal high-frequency spam. It runs completely undetected as a standard automated terminal. Furthermore, it uses a unique "Magic Number" to securely identify and manage its own trades without interfering with your manual trades.

---

## 🌍 Open Source Roadmap
As an open-source project, ATK is constantly evolving. Here is what we are planning next:
1. **Machine Learning Integrations**: Moving beyond hardcoded RSI/MA rules to dynamic probability scoring using XGBoost or Scikit-Learn.
2. **Advanced Volatility Guards**: Implementing ATR filters to completely shut down trading during flatline regime periods.
3. **Trailing Stops**: Real-time management of open trades to lock in profits dynamically rather than relying on hard TP levels.

---

## ⚠️ Disclaimer
This software is provided for testing AI agent models and experimental purposes. Algorithmic trading in financial markets involves significant risk of loss. Always forward-test the bot extensively on a **Demo Account** before allowing it to trade with real funds.
