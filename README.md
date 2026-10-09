# Adongo Trading Kit (ATK)

The **Adongo Trading Kit (ATK)** is an automated XAUUSD (Gold) Scalping Bot designed to run with MetaTrader 5 (MT5). It uses a Smart Multi-Factor Score system to evaluate market conditions and automatically execute trades based on real-time data.

## Features

- **Automated Trading**: Runs 24/7 scanning for optimal trading opportunities.
- **Smart Multi-Factor Scoring**:
  - **RSI Quality (45%)**: Rejects overbought/oversold and targets momentum sweet spots.
  - **Trend Strength (35%)**: Evaluates price relative to the 50-period Moving Average.
  - **Session Timing (20%)**: Emphasizes high-liquidity sessions (London/NY overlap).
- **Safe Testing**: Includes a dry-run mode (`TEST_ONE_CYCLE.bat`) that lets you test the bot without placing real orders.
- **Risk Management**: Configurable maximum daily trades, concurrent positions, and cooldown periods.
- **Live Monitoring**: Track win rates, P&L, recent trades, and live signals through a built-in dashboard or status script.

## Getting Started

### 1. Requirements

- **MetaTrader 5**: The bot requires the MT5 terminal to be installed and running.
- **Python**: Ensure Python is installed along with the required dependencies in `requirements.txt`.

### 2. Setup

1. Rename `.env.example` to `.env` and fill in your MT5 login credentials (these are kept locally and never shared).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Open MetaTrader 5 and ensure it is connected to your broker.
4. Update configuration in `config/settings.yaml` as desired.

### 3. Running the Bot

Use the provided batch files to operate the bot:

- **`TEST_ONE_CYCLE.bat`**: Run this first for a safe dry-run test (no real money).
- **`START_BOT.bat`**: Start the bot for continuous live trading.
- **`CHECK_STATUS.bat`**: Check the current P&L, win rate, and recent signals while the bot runs.

To stop the bot, you can either press `Ctrl+C` in the terminal or create a `STOP_BOT.txt` file in the main directory.

## Project Structure

- `src/` - Core Python source code (bot logic, MT5 integration, execution).
- `config/` - Bot configuration and settings (`settings.yaml`).
- `scripts/` - Helper scripts.
- `runs/` - Local storage for logs, trade history, and status updates (ignored by Git).
- `SETUP_AND_RUN.md` - Detailed setup instructions for running the bot.

## Disclaimer

This bot is for educational and experimental purposes. Trading in financial markets involves significant risk. Always test algorithms in a demo account or in dry-run mode before putting real capital at risk.
