import streamlit as st
import os
import subprocess
import psutil
from pathlib import Path
import MetaTrader5 as mt5

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
STOP_FILE = PROJECT_ROOT / "STOP_BOT.txt"

def load_env():
    env_vars = {"MT5_LOGIN": "", "MT5_PASSWORD": "", "MT5_SERVER": ""}
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
    # Basic check if main.py is running
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'python' in proc.info['name'].lower():
                if any('src.main' in cmd or 'src/main.py' in cmd for cmd in proc.info['cmdline']):
                    return True
        except:
            pass
    return False

def start_bot():
    if STOP_FILE.exists():
        STOP_FILE.unlink()
    
    # Start bot as subprocess
    env = os.environ.copy()
    env.update(load_env())
    subprocess.Popen(["python", "-m", "src.main"], cwd=str(PROJECT_ROOT), env=env)

def stop_bot():
    # Just touch the stop file
    STOP_FILE.write_text("STOP\n")

st.set_page_config(page_title="ATK V2 Controller", layout="wide")
st.title("ATK V2 - Bot Controller")

# Sidebar for settings
with st.sidebar:
    st.header("MT5 Credentials")
    env_vars = load_env()
    login = st.text_input("Account Login", value=env_vars.get("MT5_LOGIN", ""))
    password = st.text_input("Password", value=env_vars.get("MT5_PASSWORD", ""), type="password")
    server = st.text_input("Server", value=env_vars.get("MT5_SERVER", ""))
    
    if st.button("Save Credentials"):
        save_env(login, password, server)
        st.success("Saved to .env")

# Main Content
col1, col2 = st.columns(2)

with col1:
    st.header("Control Panel")
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

with col2:
    st.header("Live MT5 Dashboard")
    env = load_env()
    
    if st.button("Connect & Fetch Account Details"):
        if not mt5.initialize():
            st.error("Failed to initialize MetaTrader 5.")
        else:
            if mt5.login(int(env["MT5_LOGIN"]), password=env["MT5_PASSWORD"], server=env["MT5_SERVER"]):
                acc = mt5.account_info()
                if acc:
                    st.metric("Balance", f"${acc.balance:,.2f}")
                    st.metric("Equity", f"${acc.equity:,.2f}")
                    st.metric("Free Margin", f"${acc.margin_free:,.2f}")
                    
                    st.subheader("Open Positions")
                    positions = mt5.positions_get()
                    if positions:
                        for pos in positions:
                            st.write(f"**{pos.symbol}**: {pos.volume} lots | Profit: ${pos.profit}")
                    else:
                        st.write("No open positions.")
            else:
                st.error("Failed to connect to account. Check credentials.")
            mt5.shutdown()
