# MT5 (Exness) quick start

1. Install dependencies:
   - `python -m pip install -r requirements.txt`
   - `python -m playwright install chromium`

2. Credentials:
   - This project reads from `.env`.
   - If missing, copy `.env.example` to `.env` and fill:
     - `MT5_LOGIN`
     - `MT5_PASSWORD`
     - `MT5_SERVER` (your Exness MT5 server name)

3. Check `config/settings.yaml`:
   - `broker.backend: "mt5"`
   - `mt5.enabled: true`
   - `mt5.lot: 0.01`
   - `mt5.dry_run: true` (first run safety)
   - `analysis.watchlist` includes `XAUUSD`

4. Run one cycle:
   - `python -m src.main --run-once`

5. Inspect dashboard:
   - `http://127.0.0.1:8765/`
   - Live status JSON and screenshots are in `runs/`

6. If dry run looks correct, switch to real demo orders:
   - Set `mt5.dry_run: false`
   - Run: `python -m src.main`

## Start command (automatic mode)

- Start bot continuously:
  - `python -m src.main`
- Stop bot:
  - Create file `STOP_BOT.txt` in project root, or stop terminal with `Ctrl + C`.

## Exact startup flow (recommended)

1. Keep `mt5.dry_run: true`
2. Run: `python -m src.main --run-once`
3. Confirm request data in logs/dashboard
4. Set `mt5.dry_run: false`
5. Run live demo auto-trading: `python -m src.main`

Notes:
- This bot computes TP1..TP4, but MT5 market order natively supports one TP per order.
- Current implementation places TP1 on the order ticket and logs TP2..TP4 in run details.
- If Exness symbol differs (e.g., `XAUUSDm`), set `mt5.symbol_map.XAUUSD` accordingly.

