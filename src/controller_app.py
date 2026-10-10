import streamlit as st
import os
import subprocess
import psutil
from pathlib import Path
import MetaTrader5 as mt5
import pandas as pd
import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
STOP_FILE = PROJECT_ROOT / "STOP_BOT.txt"

def load_env():
    env_vars = {"MT5_LOGIN": "", "MT5_PASSWORD": "", "MT5_SERVER": "Exness-MT5Trial9"}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars

def save_env(login, password, server):
    lines = [
        f"MT5_LOGIN={login}",
        f"MT5_PASSWORD={password}",
        f"MT5_SERVER={server}"
    ]
    ENV_FILE.write_text("\n".join(lines), encoding="utf-8")

def is_bot_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'python' in proc.info['name'].lower():
                if any('src.main' in cmd or 'src/main.py' in cmd for cmd in proc.info['cmdline']):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def start_bot():
    if STOP_FILE.exists():
        STOP_FILE.unlink()
    env = os.environ.copy()
    env.update(load_env())
    subprocess.Popen(["python", "-m", "src.main"], cwd=str(PROJECT_ROOT), env=env)

def stop_bot():
    STOP_FILE.write_text("STOP\n")

def is_market_closed():
    # Simple weekend check (Saturday = 5, Sunday = 6)
    now = datetime.datetime.utcnow()
    return now.weekday() >= 5

st.set_page_config(page_title="ATK Dashboard", layout="wide")
st.title("ATK Dashboard")

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")
    env_vars = load_env()
    login = st.text_input("Account Login", value=env_vars.get("MT5_LOGIN", ""))
    password = st.text_input("Password", value=env_vars.get("MT5_PASSWORD", ""), type="password")
    
    server_list = ["Exness-MT5Trial9", "Exness-Real", "MetaQuotes-Demo", "Other"]
    current_server = env_vars.get("MT5_SERVER", "Exness-MT5Trial9")
    
    selected_server = st.selectbox("Server", server_list, index=server_list.index(current_server) if current_server in server_list else 3)
    if selected_server == "Other":
        server = st.text_input("Custom Server Name", value=current_server if current_server not in server_list else "")
    else:
        server = selected_server
    
    if st.button("Save Credentials"):
        save_env(login, password, server)
        st.success("Credentials saved to .env")

# ─── MAIN CONTENT ──────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1.5])

with col1:
    st.header("Control Panel")
    
    if is_market_closed():
        st.warning("Markets are currently CLOSED (Weekend). Trading may not execute.")
        
    running = is_bot_running()
    if running:
        st.success("Bot Status: RUNNING")
        if st.button("Stop Trading", type="primary"):
            stop_bot()
            st.rerun()
    else:
        st.error("Bot Status: STOPPED")
        if st.button("Start Trading", type="primary"):
            start_bot()
            st.rerun()
            
    st.markdown("---")
    st.header("Account Overview")
    env = load_env()
    if st.button("Fetch Live Account Data"):
        if not mt5.initialize():
            st.error("Failed to initialize MetaTrader 5.")
        else:
            if mt5.login(int(env["MT5_LOGIN"]), password=env["MT5_PASSWORD"], server=env["MT5_SERVER"]):
                acc = mt5.account_info()
                if acc:
                    st.metric("Balance", f"${acc.balance:,.2f}")
                    st.metric("Equity", f"${acc.equity:,.2f}")
                    st.metric("Free Margin", f"${acc.margin_free:,.2f}")
            else:
                st.error("Failed to connect to MT5 account.")
            mt5.shutdown()

with col2:
    st.header("Live Analysis Preview")
    
    # Read the latest live status to show indicator codes and signals
    status_file = PROJECT_ROOT / "runs" / "live_status.json"
    if status_file.exists():
        import json
        try:
            status_data = json.loads(status_file.read_text(encoding="utf-8"))
            symbol = status_data.get("symbol", "Unknown")
            decision = status_data.get("decision", {})
            indicators = status_data.get("indicators", {})
            
            # Display signal intelligence
            st.subheader(f"Signal Intel: {symbol}")
            
            sig_col1, sig_col2, sig_col3 = st.columns(3)
            with sig_col1:
                st.metric("Price", f"{float(indicators.get('price', 0)):.5f}")
            with sig_col2:
                st.metric("RSI (Momentum)", f"{float(indicators.get('rsi', 0)):.2f}")
            with sig_col3:
                st.metric("MA50 (Trend)", f"{float(indicators.get('ma_50', 0)):.5f}")
            
            action = decision.get("action", "skip").upper()
            side = decision.get("side", "none").upper()
            score = decision.get("score", 0)
            
            if action == "TRADE":
                st.success(f"**Trade Executed**: {side} (Score: {score:.2f})")
            elif action == "BLOCKED":
                st.warning(f"**Trade Blocked by Risk Manager**: {side}")
            else:
                st.info(f"**Status**: Scanning for optimal setups (Current Action: SKIP)")
                
        except Exception:
            pass
            
    # Display the latest screenshot
    screenshot_dir = PROJECT_ROOT / "runs" / "screenshots"
    if screenshot_dir.exists():
        screenshots = list(screenshot_dir.glob("live_*.png"))
        if screenshots:
            # Sort by modification time to get the most recent
            latest_screenshot = max(screenshots, key=lambda p: p.stat().st_mtime)
            st.image(str(latest_screenshot), caption=f"Latest Scan: {latest_screenshot.name}", use_container_width=True)
        else:
            st.info("No live screenshots available yet. Start the bot to generate previews.")
    else:
        st.info("No live screenshots available yet. Start the bot to generate previews.")

st.markdown("---")
st.header("Recent Trade History")
if st.button("Load History from MT5"):
    if mt5.initialize() and mt5.login(int(env["MT5_LOGIN"]), password=env["MT5_PASSWORD"], server=env["MT5_SERVER"]):
        now = datetime.datetime.now()
        from_date = now - datetime.timedelta(days=7)
        deals = mt5.history_deals_get(from_date, now)
        if deals:
            df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
            df['time'] = pd.to_datetime(df['time'], unit='s')
            display_cols = ['time', 'symbol', 'deal', 'type', 'volume', 'price', 'profit']
            # Filter out generic deposits if preferred, or just show all
            st.dataframe(df[display_cols].sort_values('time', ascending=False), use_container_width=True)
        else:
            st.write("No trades found in the last 7 days.")
        mt5.shutdown()
    else:
        st.error("Could not connect to MT5 to fetch history.")
