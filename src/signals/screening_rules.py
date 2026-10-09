from __future__ import annotations

"""
Smart XAUUSD Screening Rules
============================
Replaces the basic MA/RSI threshold filter with a multi-factor scoring
system optimised for higher win-rate scalping on XAUUSD.

Score components (all weighted 0-1, combined to a final 0-1 score):
  1. Trend strength   – how far price is from the MA (normalised)
  2. RSI quality      – RSI in the "momentum sweet-spot", not exhausted
  3. Session timing   – trade during peak XAUUSD liquidity windows
  4. Anti-overextension – penalise setups where RSI is too extreme

Entry gate (ALL must be true):
  Long  : price > MA50  AND  55 <= RSI < 72   (momentum, not overbought)
  Short : price < MA50  AND  28 < RSI <= 45   (momentum, not oversold)

Score threshold (set in settings.yaml execution.min_signal_score):
  Default 0.60 — lower than before but gated by stricter quality checks.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ── Session windows (UTC hours) ───────────────────────────────────────────────
# XAUUSD is most volatile during London (07-16 UTC) and NY (13-21 UTC).
# Best scalping: London-NY overlap 13-16 UTC.
_SESSION_WEIGHTS: list[tuple[int, int, float]] = [
    (13, 16, 1.0),   # London-NY overlap  → full weight
    (8,  13, 0.8),   # London session     → good
    (16, 21, 0.7),   # NY session         → acceptable
    (0,  8,  0.3),   # Asian / off-hours  → weak
    (21, 24, 0.3),   # Late NY / rollover → weak
]


def _session_weight() -> float:
    """Return a 0-1 multiplier based on current UTC hour."""
    hour = datetime.now(timezone.utc).hour
    for start, end, weight in _SESSION_WEIGHTS:
        if start <= hour < end:
            return weight
    return 0.3


def _rsi_quality_score(rsi: float, side: str) -> float:
    """
    Returns 0-1 quality score based on how well RSI supports the trade.
    Sweet spots (avoid exhausted RSI > 75 long or < 25 short):
      Long  : 55-72  → linear from 0 at 55 to 1.0 at 63, back to 0 at 72
      Short : 28-45  → mirror image
    """
    if side == "long":
        if rsi < 55 or rsi >= 72:
            return 0.0
        # Peak quality around RSI = 63
        peak = 63.0
        if rsi <= peak:
            return (rsi - 55.0) / (peak - 55.0)
        else:
            return (72.0 - rsi) / (72.0 - peak)
    else:  # short
        if rsi > 45 or rsi <= 28:
            return 0.0
        peak = 37.0
        if rsi >= peak:
            return (45.0 - rsi) / (45.0 - peak)
        else:
            return (rsi - 28.0) / (peak - 28.0)


def _trend_strength_score(price: float, ma50: float) -> float:
    """
    Distance of price from MA50 as a normalised score.
    Cap at 2% distance (very strong trend) = 1.0.
    Small distances = weaker trend signal.
    """
    if ma50 == 0:
        return 0.0
    dist_pct = abs(price - ma50) / abs(ma50)
    # Normalise: 0.05% → 0.025, 1% → 0.5, >=2% → 1.0
    score = min(dist_pct / 0.02, 1.0)
    return float(score)


class ScreeningRules:
    """
    Multi-factor screener for XAUUSD scalping.

    Config keys used (from analysis.screening / scalping.screening):
      rsi_long_threshold   – minimum RSI for long  (default 55)
      rsi_short_threshold  – maximum RSI for short (default 45)
      rsi_long_max         – RSI ceiling for long  (default 72)
      rsi_short_min        – RSI floor for short   (default 28)
      session_filter       – bool, skip off-session signals (default true)
      min_session_weight   – minimum session weight to trade (default 0.3)
    """

    def __init__(self, screening_cfg: Dict[str, Any]) -> None:
        self.rsi_long_min  = float(screening_cfg.get("rsi_long_threshold", 55))
        self.rsi_long_max  = float(screening_cfg.get("rsi_long_max", 72))
        self.rsi_short_max = float(screening_cfg.get("rsi_short_threshold", 45))
        self.rsi_short_min = float(screening_cfg.get("rsi_short_min", 28))
        self.session_filter = bool(screening_cfg.get("session_filter", True))
        self.min_session_weight = float(screening_cfg.get("min_session_weight", 0.3))

    def decide(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        price = indicators.get("price")
        ma50  = indicators.get("ma50")
        rsi14 = indicators.get("rsi14")

        # ── 1. Data quality gate ─────────────────────────────────────────────
        if price is None or ma50 is None or rsi14 is None:
            return self._skip("missing_indicator_values", price, ma50, rsi14)

        price = float(price)
        ma50  = float(ma50)
        rsi14 = float(rsi14)

        if price == ma50:
            return self._skip("price_equals_ma", price, ma50, rsi14)

        # ── 2. Session filter ─────────────────────────────────────────────────
        session_w = _session_weight()
        if self.session_filter and session_w < self.min_session_weight:
            return self._skip("off_session", price, ma50, rsi14, extra={"session_weight": session_w})

        # ── 3. Trend direction ────────────────────────────────────────────────
        trend_side: str = "long" if price > ma50 else "short"

        # ── 4. RSI momentum gate (strict quality zone) ────────────────────────
        if trend_side == "long":
            rsi_ok = self.rsi_long_min <= rsi14 < self.rsi_long_max
        else:
            rsi_ok = self.rsi_short_min < rsi14 <= self.rsi_short_max

        if not rsi_ok:
            reason = "rsi_overbought" if (trend_side == "long" and rsi14 >= self.rsi_long_max) \
                else "rsi_oversold" if (trend_side == "short" and rsi14 <= self.rsi_short_min) \
                else "rsi_neutral"
            return self._skip(reason, price, ma50, rsi14)

        # ── 5. Composite score ────────────────────────────────────────────────
        rsi_q   = _rsi_quality_score(rsi14, trend_side)
        trend_s = _trend_strength_score(price, ma50)

        # Weighted combination: RSI quality 45%, trend strength 35%, session 20%
        score = (rsi_q * 0.45) + (trend_s * 0.35) + (session_w * 0.20)
        score = round(min(max(score, 0.0), 1.0), 4)

        return {
            "action": "trade",
            "side":   trend_side,
            "score":  score,
            "reason": "smart_multi_factor",
            "inputs": {
                "price":          price,
                "ma50":           ma50,
                "rsi14":          rsi14,
                "rsi_quality":    round(rsi_q, 4),
                "trend_strength": round(trend_s, 4),
                "session_weight": round(session_w, 4),
            },
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _skip(
        reason: str,
        price: Optional[float],
        ma50: Optional[float],
        rsi14: Optional[float],
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "action": "skip",
            "side":   "none",
            "score":  None,
            "reason": reason,
            "inputs": {"price": price, "ma50": ma50, "rsi14": rsi14},
        }
        if extra:
            d.update(extra)
        return d
