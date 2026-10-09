from __future__ import annotations

from typing import Any, Dict, List, Optional

from playwright.async_api import Locator, Page

from ..config import TradingViewConfig


def _fmt_price(x: float) -> str:
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


class TradingViewUITradeExecutor:
    """
    Best-effort UI automation for TradingView paper / broker panel.

    Notes:
    - Many layouts expose one primary Take profit field; TP2–TP4 may not exist in DOM.
      We fill every field we can find; remaining TPs are returned in `details` for alerts/manual.
    - Gold (XAUUSD) and FX need different point scales: tune `scalping.sl_points` and `tp_rr` in YAML.
    """

    def __init__(
        self,
        tv_cfg: TradingViewConfig,
        quantity: float,
        min_signal_score: float,
    ):
        self.tv_cfg = tv_cfg
        self.quantity = float(quantity)
        self.min_signal_score = float(min_signal_score)

    async def place_paper_order(
        self,
        page: Page,
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

        details: Dict[str, Any] = {
            "bracket_requested": bracket,
            "filled_sl": False,
            "filled_tp": [False, False, False, False],
        }

        try:
            await page.wait_for_timeout(1200)

            opened = await self._try_click(
                page,
                [
                    "text=Trade",
                    "text=Trading",
                    "text=New Order",
                    "[data-name='trade']",
                ],
            )

            if side == "long":
                clicked = await self._try_click(page, ["text=Buy", "text=Long"])
            else:
                clicked = await self._try_click(page, ["text=Sell", "text=Short"])

            if not clicked and not opened:
                return {
                    "success": False,
                    "error": "trade_ui_not_found",
                    "symbol": symbol,
                    "side": side,
                    "details": details,
                }

            await self._try_fill_quantity(page, self.quantity)

            if bracket:
                sl = float(bracket["sl"])
                tps = [float(bracket["tp1"]), float(bracket["tp2"]), float(bracket["tp3"]), float(bracket["tp4"])]
                details["filled_sl"] = await self._try_fill_stop_loss(page, sl)
                for i, price in enumerate(tps):
                    details["filled_tp"][i] = await self._try_fill_take_profit_n(page, i, price)

            confirmed = await self._try_click(
                page,
                [
                    "text=Place Order",
                    "text=Submit",
                    "text=Confirm",
                    "text=Create order",
                ],
            )
            if not confirmed:
                # Some layouts submit on Buy/Sell directly.
                pass

            acknowledged = await self._try_detect_ack(page)

            filled_any_tp = any(details["filled_tp"]) if bracket else False
            if bracket:
                success = bool(acknowledged) and bool(details["filled_sl"]) and filled_any_tp
            else:
                success = bool(acknowledged)

            if bracket and not success:
                details["error_hint"] = (
                    "Could not confirm SL/TP in UI. Check TradingView order panel layout "
                    "or enter SL/TP manually; see bracket_requested prices in logs."
                )

            return {
                "success": success,
                "error": None if success else (details.get("error_hint") or "order_not_acknowledged"),
                "symbol": symbol,
                "side": side,
                "quantity": self.quantity,
                "acknowledged": bool(acknowledged),
                "details": details,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "side": side,
                "details": details,
            }

    async def _try_click(self, page: Page, selectors: List[str]) -> bool:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() == 0:
                    continue
                await loc.click(timeout=2500)
                await page.wait_for_timeout(600)
                return True
            except Exception:
                continue
        return False

    async def _try_fill_quantity(self, page: Page, quantity: float) -> None:
        possible_inputs = [
            "input[name='quantity']",
            "input[placeholder*='Quantity' i]",
            "input[placeholder*='Size' i]",
            "input[placeholder*='Units' i]",
            "input[type='text']",
        ]
        for sel in possible_inputs:
            try:
                inp = page.locator(sel).first
                if await inp.count() == 0:
                    continue
                await inp.fill(str(quantity))
                await page.wait_for_timeout(400)
                return
            except Exception:
                continue

    async def _try_fill_stop_loss(self, page: Page, price: float) -> bool:
        val = _fmt_price(price)
        return await self._fill_by_nearby_label(
            page,
            ["Stop", "SL", "Stop loss", "Stop Loss"],
            val,
        )

    async def _try_fill_take_profit_n(self, page: Page, index: int, price: float) -> bool:
        val = _fmt_price(price)
        if index == 0:
            return await self._fill_by_nearby_label(
                page,
                ["Take profit", "TP", "Target", "Limit"],
                val,
            )
        return await self._fill_by_nearby_label(
            page,
            [f"Take profit {index + 1}", f"TP{index + 1}", f"TP {index + 1}"],
            val,
        )

    async def _fill_by_nearby_label(self, page: Page, label_keywords: List[str], value: str) -> bool:
        for kw in label_keywords:
            try:
                label = page.locator(f"text={kw}").first
                if await label.count() == 0:
                    continue
                box = await label.bounding_box()
                if box is None:
                    continue
                candidates = page.locator("input:visible")
                n = await candidates.count()
                best: Optional[Locator] = None
                best_dy = 1e9
                for i in range(min(n, 80)):
                    inp = candidates.nth(i)
                    try:
                        ibox = await inp.bounding_box()
                        if ibox is None:
                            continue
                        dy = abs(ibox["y"] - box["y"])
                        dx = abs(ibox["x"] - box["x"])
                        if dy < 120 and dx < 420 and dy < best_dy:
                            best_dy = dy
                            best = inp
                    except Exception:
                        continue
                if best is not None:
                    await best.fill(value)
                    await page.wait_for_timeout(350)
                    return True
            except Exception:
                continue

        # Fallback: placeholder search
        for ph in ["Stop", "SL", "Take profit", "TP"]:
            try:
                loc = page.locator(f"input[placeholder*='{ph}' i]").first
                if await loc.count() == 0:
                    continue
                await loc.fill(value)
                await page.wait_for_timeout(350)
                return True
            except Exception:
                continue
        return False

    async def _try_detect_ack(self, page: Page) -> bool:
        ack_patterns = [
            "Order placed",
            "Filled",
            "Position opened",
            "Order submitted",
            "Working order",
        ]
        for p in ack_patterns:
            try:
                loc = page.locator(f"text={p}").first
                if await loc.count() == 0:
                    continue
                txt = (await loc.inner_text(timeout=1500)).strip()
                if len(txt) > 0:
                    return True
            except Exception:
                continue
        return False
