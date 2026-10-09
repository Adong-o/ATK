from __future__ import annotations

"""
Status Reporter – prints a live summary of bot performance from the SQLite DB.
Run with:  python -m src.utils.status_report
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runs" / "state.db"


def _risk_state_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runs" / "risk_state.json"


def _live_status_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runs" / "live_status.json"


def report() -> None:
    db = _db_path()
    if not db.exists():
        print("No state.db found yet — bot has not run.")
        return

    conn = sqlite3.connect(str(db))

    # ── Overall stats ─────────────────────────────────────────────────────────
    cur = conn.execute(
        """
        SELECT
            COUNT(*)                          AS total,
            SUM(CASE WHEN action='trade' THEN 1 ELSE 0 END)   AS trades,
            SUM(CASE WHEN action='trade' AND success=1 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN action='trade' AND success=0 THEN 1 ELSE 0 END) AS fails,
            SUM(CASE WHEN action='skip'  THEN 1 ELSE 0 END)   AS skips,
            SUM(CASE WHEN action='error' THEN 1 ELSE 0 END)   AS errors
        FROM executions
        """
    )
    row = cur.fetchone()
    total, trades, wins, fails, skips, errors = (row or (0,)*6)
    win_rate = (wins / trades * 100) if trades else 0.0

    # ── Today stats ───────────────────────────────────────────────────────────
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cur2 = conn.execute(
        """
        SELECT
            SUM(CASE WHEN action='trade' THEN 1 ELSE 0 END)              AS trades,
            SUM(CASE WHEN action='trade' AND success=1 THEN 1 ELSE 0 END) AS wins
        FROM executions
        WHERE ts_utc LIKE ?
        """,
        (f"{today}%",),
    )
    row2 = cur2.fetchone()
    today_trades, today_wins = (row2 or (0, 0))
    today_win_rate = (today_wins / today_trades * 100) if today_trades else 0.0

    # ── Recent trades ─────────────────────────────────────────────────────────
    cur3 = conn.execute(
        """
        SELECT e.ts_utc, e.symbol, e.side, e.action, e.score, e.success, e.error, e.details_json
        FROM executions e
        WHERE e.action = 'trade'
        ORDER BY e.id DESC
        LIMIT 10
        """
    )
    recent = cur3.fetchall()
    conn.close()

    # ── Risk state ────────────────────────────────────────────────────────────
    risk = {}
    rsp = _risk_state_path()
    if rsp.exists():
        try:
            risk = json.loads(rsp.read_text())
        except Exception:
            pass

    # ── Live status ───────────────────────────────────────────────────────────
    live = {}
    lsp = _live_status_path()
    if lsp.exists():
        try:
            live = json.loads(lsp.read_text())
        except Exception:
            pass

    # ── Print ─────────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sep = "─" * 56

    print()
    print(sep)
    print(f"  XAUUSD BOT STATUS  •  {now}")
    print(sep)

    print(f"\n  ALL TIME")
    print(f"  {'Total executions':<28}: {total}")
    print(f"  {'Trade signals sent':<28}: {trades}")
    print(f"  {'Successful orders':<28}: {wins}")
    print(f"  {'Failed orders':<28}: {fails}")
    print(f"  {'Skipped (no signal)':<28}: {skips}")
    print(f"  {'Errors':<28}: {errors}")
    print(f"  {'Win rate':<28}: {win_rate:.1f}%")

    print(f"\n  TODAY ({today})")
    print(f"  {'Trades today':<28}: {today_trades}")
    print(f"  {'Wins today':<28}: {today_wins}")
    print(f"  {'Win rate today':<28}: {today_win_rate:.1f}%")

    if risk:
        print(f"\n  RISK STATE")
        print(f"  {'Trades today (risk)':<28}: {risk.get('trades_today', 0)}")
        print(f"  {'Open positions':<28}: {risk.get('open_positions', 0)}")
        cooldown_ts = float(risk.get("cooldown_until_ts", 0))
        import time as _time
        if cooldown_ts > _time.time():
            remaining = int(cooldown_ts - _time.time())
            print(f"  {'Cooldown active':<28}: {remaining}s remaining")
        else:
            print(f"  {'Cooldown':<28}: none")

    if live:
        print(f"\n  LAST LIVE SCAN")
        print(f"  {'Symbol':<28}: {live.get('symbol', '?')}")
        print(f"  {'Timeframe':<28}: {live.get('timeframe', '?')}")
        decision = live.get("decision", {})
        print(f"  {'Decision':<28}: {decision.get('action','?')} / {decision.get('side','?')}")
        print(f"  {'Score':<28}: {decision.get('score','?')}")
        print(f"  {'Reason':<28}: {decision.get('reason','?')}")
        inds = decision.get("inputs", {})
        if inds:
            print(f"  {'Price':<28}: {inds.get('price','?')}")
            print(f"  {'MA50':<28}: {inds.get('ma50','?')}")
            print(f"  {'RSI14':<28}: {inds.get('rsi14','?')}")

    if recent:
        print(f"\n  LAST 10 TRADES")
        print(f"  {'Time (UTC)':<22} {'Side':<6} {'Score':<7} {'OK':<4} {'Note'}")
        print(f"  {'-'*22} {'-'*6} {'-'*7} {'-'*4} {'-'*20}")
        for r in recent:
            ts, sym, side, action, score, success, error, details_json = r
            ts_short = ts[:19].replace("T", " ")
            score_s = f"{score:.3f}" if score is not None else "  --- "
            ok_s = "YES" if success else "NO "
            note = ""
            if error:
                note = error[:30]
            elif details_json:
                try:
                    d = json.loads(details_json)
                    od = d.get("order_result", {})
                    if od.get("dry_run"):
                        note = "DRY RUN"
                    elif od.get("retcode"):
                        note = f"retcode:{od['retcode']}"
                except Exception:
                    pass
            print(f"  {ts_short:<22} {side:<6} {score_s:<7} {ok_s:<4} {note}")

    print()
    print(sep)
    print()


if __name__ == "__main__":
    report()
