# Adongo Trading Kit (ATK)

The **Adongo Trading Kit (ATK)** is an advanced, fully automated algorithmic trading application designed for MetaTrader 5 (MT5). 

While ATK is built as a powerful tool for **schooling and educational purposes** to understand algorithmic market analysis, it is a **production-ready 100% functional trading system**. It can be deployed on a live real-money account or a demo account across any broker (like Exness, MetaQuotes, etc.). 

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

## Disclaimer
This software is provided for educational and experimental purposes. Algorithmic trading in financial markets involves significant risk of loss. Always forward-test the bot extensively on a **Demo Account** before allowing it to trade with real funds.
