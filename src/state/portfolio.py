from __future__ import annotations

from typing import Any, Dict


class PaperPortfolio:
    """
    MVP placeholder for paper portfolio state.
    TradingView UI automation may not reliably expose PnL; risk controls for now
    focus on order/attempt limits + cooldown.
    """

    def __init__(self) -> None:
        self.last_order: Dict[str, Any] | None = None

    def apply_execution_stub(self, order_result: Dict[str, Any]) -> None:
        self.last_order = dict(order_result)

