# Adongo Trading Kit (ATK) V2

The **Adongo Trading Kit (ATK)** is an automated algorithmic trading system designed for MetaTrader 5 (MT5). Version 2 transforms ATK into a complete trading platform with a sleek web interface, dynamic risk management, and multi-asset scanning.

## What's New in V2?
- **Web Controller UI**: A minimal, clean dashboard to manage credentials, monitor live account equity/balance, and start/stop the bot in one click.
- **Dynamic Lot Sizing**: The bot now scales your position sizes automatically. It reads your live account balance and risks exactly **1%** per trade based on the calculated Stop Loss distance.
- **Multi-Pair Watchlist**: Scans multiple instruments simultaneously (XAUUSD, EURUSD, GBPUSD, USDJPY) instead of being locked to a single pair.

## Core Features
- **Smart Multi-Factor Scoring**: Evaluates momentum (RSI), trend strength (MA50), and session timing.
- **Automated Trading**: Runs 24/7 scanning for optimal trading opportunities.
- **Live MT5 Integration**: Connects directly to your local MetaTrader 5 terminal via Python.

## Getting Started

### 1. Requirements
- **MetaTrader 5**: Ensure the MT5 terminal is installed on your Windows machine.
- **Python 3.9+**: Make sure Python is installed.

### 2. Setup & Installation
1. Clone this repository or download the folder.
2. Open a terminal in the folder and install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. How to Run the Live UI
We have moved away from running raw scripts in the background. ATK now provides a web interface.

1. Double-click the **`START_CONTROLLER.bat`** file on your desktop/folder.
   *(Alternatively, run `python -m streamlit run src/controller_app.py` in your terminal).*
2. Your browser will automatically open the Web UI at **`http://localhost:8501`**.
3. In the sidebar, enter your **MT5 Account Login, Password, and Server** and click "Save Credentials".
4. Click **"Connect & Fetch Account Details"** to verify your balance and live positions.
5. Click **"Start Trading"** to launch the bot!

## Project Structure
- `src/controller_app.py` - The minimal Streamlit Web UI.
- `src/execution/mt5_terminal.py` - Core execution engine with Dynamic Lot Sizing.
- `config/settings.yaml` - Bot parameters, risk percentage, and watchlist pairs.
- `runs/` - Local storage for logs and state databases (ignored by Git).
- `START_CONTROLLER.bat` - The primary entry point for users.

## Disclaimer
This software is for educational purposes. Trading in financial markets involves significant risk. Always test algorithms in a demo account or with dry-run enabled before putting real capital at risk.
