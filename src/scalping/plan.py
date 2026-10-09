from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class BracketPlan:
    """Prices derived from entry, side, SL distance, and TP multiples of that distance."""

    entry: float
    side: str  # "long" | "short"
    sl: float
    tp1: float
    tp2: float
    tp3: float
    tp4: float
    sl_distance: float
    tp_distances: Tuple[float, float, float, float]


def build_bracket_plan(
    entry: float,
    side: str,
    sl_points: float,
    tp_rr: Tuple[float, float, float, float],
) -> BracketPlan:
    """
    sl_points: absolute distance in *price units* from entry to stop (always positive).
    tp_rr: each TP is `entry +/- sl_points * rr` in the profit direction.
    """
    if sl_points <= 0:
        raise ValueError("sl_points must be positive")
    if side == "long":
        sl = entry - sl_points
        tps = tuple(entry + sl_points * rr for rr in tp_rr)
    elif side == "short":
        sl = entry + sl_points
        tps = tuple(entry - sl_points * rr for rr in tp_rr)
    else:
        raise ValueError("side must be long or short")

    return BracketPlan(
        entry=entry,
        side=side,
        sl=sl,
        tp1=tps[0],
        tp2=tps[1],
        tp3=tps[2],
        tp4=tps[3],
        sl_distance=sl_points,
        tp_distances=tuple(abs(tps[i] - entry) for i in range(4)),
    )


def plan_to_dict(plan: BracketPlan) -> Dict[str, Any]:
    return {
        "entry": plan.entry,
        "side": plan.side,
        "sl": plan.sl,
        "tp1": plan.tp1,
        "tp2": plan.tp2,
        "tp3": plan.tp3,
        "tp4": plan.tp4,
        "sl_distance": plan.sl_distance,
        "tp_distances": list(plan.tp_distances),
    }
