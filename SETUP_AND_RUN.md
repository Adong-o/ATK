# 🤖 XAUUSD Scalping Bot — Complete Setup & Run Guide

## ⚡ Quick Start (3 Steps)

### STEP 1 — Install MetaTrader 5 (REQUIRED — one-time)

> **This is the only thing you must do manually. Everything else is automatic.**

1. Download MT5 from Exness:
   👉 **https://one.exness-track.com/a/download/terminal**
   *(or go to exness.com → My Account → Download MT5)*

2. Install it (click through the installer)

3. Open MetaTrader 5 and log in:
   - **Login:** `435147516`
   - **Password:** `Jakes@005`
   - **Server:** `ExnessKE-MT5Trial9`

4. **Leave MT5 open** — the bot connects to it automatically.

---

### STEP 2 — Run the Bot

Double-click one of these files in the `bot` folder:

| File | What it does |
|------|--------------|
| `TEST_ONE_CYCLE.bat` | ✅ **Start here** — safe dry run, no real orders |
| `START_BOT.bat` | 🚀 Continuous live trading (runs 24/7) |
| `CHECK_STATUS.bat` | 📊 View P&L, win rate, recent trades |

---

### STEP 3 — Go Live

After `TEST_ONE_CYCLE.bat` succeeds:

1. Open `config/settings.yaml`
2. Change `dry_run: true` → `dry_run: false`
3. Double-click `START_BOT.bat`

---

## 📊 Monitoring the Bot

### Check status anytime:
```
Double-click CHECK_STATUS.bat
```
Shows: win rate, trades today, last 10 signals, live scan results.

### Dashboard (while bot is running):
Open browser → **http://127.0.0.1:8765/**

### Log files:
All logs saved to `runs/logs/`

### Live status JSON:
`runs/live_status.json` — updated after every scan

---

## 🧠 Trading Algorithm

The bot uses a **Smart Multi-Factor Score** system:

| Factor | Weight | What it checks |
|--------|--------|----------------|
| RSI Quality | 45% | RSI in momentum sweet-spot (55-72 for long, 28-45 for short) — rejects overbought/oversold |
| Trend Strength | 35% | How far price is above/below MA50 |
| Session Timing | 20% | XAUUSD peak hours bonus |

**Entry rules (ALL must be true):**
- **LONG:** Price > MA50 AND RSI between 55–72
- **SHORT:** Price < MA50 AND RSI between 28–45

**Session weights (UTC):**
- 13:00–16:00 = Full weight ✅ (London + NY overlap — best for XAUUSD)
- 08:00–13:00 = 80% (London session)
- 16:00–21:00 = 70% (NY session)
- Off-hours = 30%

**Take profit levels:** 1.5× / 2.5× / 3.5× / 5.0× the stop distance

---

## 🛑 Stopping the Bot

**Option A:** Press `Ctrl+C` in the terminal window

**Option B:** Create a file called `STOP_BOT.txt` in the bot folder  
```
echo. > STOP_BOT.txt
```

---

## 🔧 Key Settings (`config/settings.yaml`)

```yaml
mt5:
  dry_run: true    # ← change to false to send real orders
  lot: 0.01        # ← trade size (0.01 = micro lot)

risk:
  max_trades_per_day: 5       # max trades per day
  max_concurrent_positions: 1 # only 1 open trade at a time
  cooldown_seconds: 300       # wait 5min after a failed order

execution:
  min_signal_score: 0.55      # raise to 0.70+ for fewer but higher quality trades

scalping:
  interval_seconds: 120       # scan every 2 minutes
  sl_points: 5.0              # stop loss distance in price units ($5 for XAUUSD)
```

---

## ❓ Troubleshooting

| Error | Fix |
|-------|-----|
| `terminal64.exe not found` | Install MT5 (Step 1 above) |
| `MT5 login failed` | Check .env credentials, ensure MT5 is open |
| `symbol_select_failed` | In MT5: right-click MarketWatch → add XAUUSD |
| Bot scans but never trades | Signal score too low — check `runs/live_status.json` |
| `IPC initialize failed` | MT5 terminal is closed — reopen it |

---

## 📁 File Structure

```
bot/
├── START_BOT.bat          ← Double-click to start trading
├── TEST_ONE_CYCLE.bat     ← Safe dry run test
├── CHECK_STATUS.bat       ← View P&L and status
├── .env                   ← MT5 credentials (DO NOT SHARE)
├── config/
│   └── settings.yaml      ← All bot settings
├── src/
│   ├── main.py            ← Entry point
│   ├── signals/
│   │   └── screening_rules.py  ← Trading algorithm
│   └── execution/
│       └── mt5_terminal.py     ← MT5 order sender
└── runs/
    ├── state.db           ← Trade history
    ├── live_status.json   ← Latest scan result
    └── logs/              ← Log files
```
