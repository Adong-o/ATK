from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..config import RiskConfig


def _utc_day_key() -> str:
    # Daily limits anchored to UTC to avoid timezone ambiguity.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class RiskManager:
    """
    Risk controls (MVP):
    - Max concurrent positions (tracked crudely as "open_positions" count)
    - Max trades/day
    - Cooldown after a failed execution attempt
    - Circuit breaker placeholder for daily loss fraction (PnL wiring can be added later)
    """

    def __init__(self, risk_cfg: RiskConfig):
        self.risk_cfg = risk_cfg
        self._state_path = Path(__file__).resolve().parents[2] / "runs" / "risk_state.json"
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        try:
            if self._state_path.exists():
                return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "day_key": _utc_day_key(),
            "trades_today": 0,
            "open_positions": 0,
            "cooldown_until_ts": 0.0,
            "daily_loss_fraction": 0.0,  # placeholder
        }

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(self._state, ensure_ascii=True, indent=2), encoding="utf-8")

    def _maybe_roll_day(self) -> None:
        day_key = _utc_day_key()
        if self._state.get("day_key") != day_key:
            self._state.update(
                {
                    "day_key": day_key,
                    "trades_today": 0,
                    "open_positions": 0,
                    "cooldown_until_ts": 0.0,
                    # Preserve daily_loss_fraction reset.
                    "daily_loss_fraction": 0.0,
                }
            )
            self._save_state()

    def can_trade(self, symbol: str, side: str, score: Optional[float]) -> Tuple[bool, str]:
        _ = symbol, side, score
        self._maybe_roll_day()

        now = time.time()
        if now < float(self._state.get("cooldown_until_ts", 0.0)):
            return False, "cooldown_active"

        trades_today = int(self._state.get("trades_today", 0))
        if trades_today >= self.risk_cfg.max_trades_per_day:
            return False, "max_trades_per_day_reached"

        open_positions = int(self._state.get("open_positions", 0))
        if open_positions >= self.risk_cfg.max_concurrent_positions:
            return False, "max_concurrent_positions_reached"

        # Circuit breaker placeholder: daily_loss_fraction is currently not computed from broker/PnL.
        daily_loss_fraction = float(self._state.get("daily_loss_fraction", 0.0))
        if daily_loss_fraction >= self.risk_cfg.max_daily_loss_fraction:
            return False, "daily_loss_fraction_exceeded"

        return True, "ok"

    def record_trade_attempt(self, success: bool) -> None:
        self._maybe_roll_day()
        self._state["trades_today"] = int(self._state.get("trades_today", 0)) + 1

        if success:
            # MVP assumption: successful UI trade opens a position until we learn otherwise.
            self._state["open_positions"] = int(self._state.get("open_positions", 0)) + 1
        else:
            cooldown_until = time.time() + float(self.risk_cfg.cooldown_seconds)
            self._state["cooldown_until_ts"] = cooldown_until

        self._save_state()

