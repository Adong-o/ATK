from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import MT5Config

# ── Common install paths to probe when terminal_path is left blank ────────────
_MT5_CANDIDATE_PATHS: List[str] = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\Exness MT5\terminal64.exe",
    r"C:\Program Files (x86)\Exness MT5\terminal64.exe",
    r"C:\Program Files\Exness\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5 Exness\terminal64.exe",
]


def _find_terminal_path() -> Optional[str]:
    """
    Locate terminal64.exe by checking:
      1. %APPDATA%\\MetaQuotes\\Terminal\\<UUID>\\terminal64.exe  (broker-specific installs)
      2. Hardcoded common Program Files paths.
    Returns the first path found, or None.
    """
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        mq_terminal = Path(appdata) / "MetaQuotes" / "Terminal"
        if mq_terminal.exists():
            for child in mq_terminal.iterdir():
                exe = child / "terminal64.exe"
                if exe.exists():
                    return str(exe)

    for p in _MT5_CANDIDATE_PATHS:
        if Path(p).exists():
            return p

    return None


def _is_mt5_process_running() -> bool:
    """Return True if terminal64.exe is in the Windows process list."""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/NH"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return "terminal64.exe" in output
    except Exception:
        return False


def _launch_mt5_detached(terminal_path: str) -> None:
    """Start MT5 as a detached background process (fire and forget)."""
    subprocess.Popen(
        [terminal_path],
        close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )


class MT5TerminalExecutor:
    """
    Sends market orders to the local MetaTrader 5 terminal via the Python API.

    Startup sequence
    ────────────────
    1. Auto-detect terminal64.exe if ``mt5.terminal_path`` is blank in settings.
    2. If MT5 is not already running, launch it automatically.
    3. Retry ``mt5.initialize()`` up to ``_MAX_RETRIES`` times with backoff,
       so the bot survives a slow MT5 startup.
    4. Login with credentials from .env and confirm connection.
    """

    _MAX_RETRIES: int = 12       # give MT5 ~72 s to start
    _RETRY_DELAY_S: int = 6      # seconds between init retries
    _LAUNCH_WAIT_S: int = 10     # seconds to wait after auto-launching MT5

    def __init__(self, mt5_cfg: MT5Config, min_signal_score: float) -> None:
        self.cfg = mt5_cfg
        self.min_signal_score = float(min_signal_score)
        self._mt5: Any = None
        self._ready: bool = False

    # ── Public async interface ────────────────────────────────────────────────

    async def initialize(self) -> None:
        if self._ready:
            return
        await asyncio.to_thread(self._initialize_sync)

    async def shutdown(self) -> None:
        if not self._ready or self._mt5 is None:
            return
        await asyncio.to_thread(self._shutdown_sync)

    async def place_order(
        self,
        symbol: str,
        side: str,
        score: Optional[float],
        bracket: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if score is None or score < self.min_signal_score:
            return {
                "success": False,
                "error": "score_below_min_signal_score",
                "symbol": symbol,
                "side": side,
            }
        return await asyncio.to_thread(self._place_order_sync, symbol, side, bracket)

    # ── Sync helpers (run in thread pool) ────────────────────────────────────

    def _initialize_sync(self) -> None:
        # 1. Import the package
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "The MetaTrader5 Python package is not installed.\n"
                "Fix: pip install MetaTrader5"
            ) from exc

        # 2. Read credentials
        login_s  = os.environ.get(self.cfg.login_env, "")
        password = os.environ.get(self.cfg.password_env, "")
        server   = os.environ.get(self.cfg.server_env, "")
        if not login_s or not password or not server:
            raise RuntimeError(
                "MT5 credentials missing from environment.\n"
                f"Expected env vars: {self.cfg.login_env}, "
                f"{self.cfg.password_env}, {self.cfg.server_env}\n"
                "Fix: ensure .env exists and all three values are set."
            )
        login = int(login_s)

        # 3. Resolve terminal path
        terminal_path: Optional[str] = self.cfg.terminal_path.strip() or None
        if not terminal_path:
            terminal_path = _find_terminal_path()

        if not terminal_path:
            raise RuntimeError(
                "MetaTrader 5 desktop terminal (terminal64.exe) was NOT found.\n"
                "Fix:\n"
                "  1. Download MT5 from  https://www.metatrader5.com/en/download\n"
                "  2. Install it and log in to your Exness account.\n"
                "  3. Keep the MT5 window open, then re-run the bot.\n"
                "  OR set  mt5.terminal_path  in config/settings.yaml."
            )

        # 4. Auto-launch if not already running
        if not _is_mt5_process_running():
            print(f"[MT5] Terminal not running — launching: {terminal_path}")
            _launch_mt5_detached(terminal_path)
            print(f"[MT5] Waiting {self._LAUNCH_WAIT_S}s for MT5 to start...")
            time.sleep(self._LAUNCH_WAIT_S)
        else:
            print("[MT5] Terminal is already running.")

        # 5. Initialize with retry/backoff
        last_err: Optional[str] = None
        for attempt in range(1, self._MAX_RETRIES + 1):
            if mt5.initialize(path=terminal_path):
                print(f"[MT5] initialize() succeeded on attempt {attempt}.")
                break
            last_err = str(mt5.last_error())
            print(
                f"[MT5] Init attempt {attempt}/{self._MAX_RETRIES} failed "
                f"({last_err}) — retrying in {self._RETRY_DELAY_S}s..."
            )
            time.sleep(self._RETRY_DELAY_S)
        else:
            raise RuntimeError(
                f"MT5 initialize() failed after {self._MAX_RETRIES} attempts.\n"
                f"Last error: {last_err}\n"
                "Ensure MT5 is installed, open, and you are logged in."
            )

        # 6. Authenticate
        if not mt5.login(login=login, password=password, server=server):
            err = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(
                f"MT5 login failed: {err}\n"
                f"Credentials used → login={login}  server={server}\n"
                "Check your .env values."
            )

        info = mt5.account_info()
        balance = getattr(info, "balance", "?")
        print(f"[MT5] Connected  login={login}  server={server}  balance={balance}")
        self._mt5 = mt5
        self._ready = True

    def _shutdown_sync(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
        self._ready = False
        self._mt5 = None

    def _place_order_sync(
        self, symbol: str, side: str, bracket: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not self._ready or self._mt5 is None:
            return {
                "success": False,
                "error": "mt5_not_initialized",
                "symbol": symbol,
                "side": side,
            }

        mt5 = self._mt5
        mt5_symbol = self.cfg.symbol_map.get(symbol.upper(), symbol)

        # Enable symbol in MarketWatch
        if not mt5.symbol_select(mt5_symbol, True):
            return {
                "success": False,
                "error": f"symbol_select_failed: {mt5.last_error()}",
                "symbol": symbol,
                "mt5_symbol": mt5_symbol,
                "side": side,
            }

        tick = mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return {
                "success": False,
                "error": f"no_tick_data: {mt5.last_error()}",
                "symbol": symbol,
                "mt5_symbol": mt5_symbol,
                "side": side,
            }

        order_type = mt5.ORDER_TYPE_BUY if side == "long" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "long" else tick.bid
        sl = float(bracket["sl"])  if bracket and bracket.get("sl")  is not None else 0.0
        tp = float(bracket["tp1"]) if bracket and bracket.get("tp1") is not None else 0.0

        request: Dict[str, Any] = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       mt5_symbol,
            "volume":       float(self.cfg.lot),
            "type":         order_type,
            "price":        float(price),
            "deviation":    int(self.cfg.deviation),
            "magic":        int(self.cfg.magic),
            "comment":      "bot_xau_scalp",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if sl > 0:
            request["sl"] = sl
        if tp > 0:
            request["tp"] = tp

        # Dry-run: validate request but don't send
        if self.cfg.dry_run:
            check = mt5.order_check(request)
            check_dict = check._asdict() if hasattr(check, "_asdict") else {}
            return {
                "success":      True,
                "dry_run":      True,
                "symbol":       symbol,
                "mt5_symbol":   mt5_symbol,
                "side":         side,
                "price":        float(price),
                "request":      request,
                "order_check":  check_dict,
                "note":         "dry_run=true — no real order sent.",
            }

        result = mt5.order_send(request)
        if result is None:
            return {
                "success":    False,
                "error":      f"order_send returned None: {mt5.last_error()}",
                "symbol":     symbol,
                "mt5_symbol": mt5_symbol,
                "side":       side,
                "request":    request,
            }

        retcode = int(getattr(result, "retcode", -1))
        ok = retcode == int(mt5.TRADE_RETCODE_DONE)
        return {
            "success":       ok,
            "error":         None if ok else f"retcode:{retcode}",
            "symbol":        symbol,
            "mt5_symbol":    mt5_symbol,
            "side":          side,
            "price":         float(price),
            "request":       request,
            "retcode":       retcode,
            "result":        result._asdict() if hasattr(result, "_asdict") else str(result),
            "tp2_tp4_note":  bracket if bracket else None,
        }
