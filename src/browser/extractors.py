from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from playwright.async_api import Page


def _parse_first_float(text: str) -> Optional[float]:
    # Accept things like "58.23", "-12.3", "1,234.56" (commas ignored).
    t = text.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", t)
    return float(m.group(0)) if m else None


class ChartDataExtractor:
    """
    MVP extractor:
    - Best-effort DOM reads for RSI(14), 50MA and the current price.
    - If extraction fails, returns `None` values so screening will `skip` safely.
    """

    def __init__(self, indicators_cfg: Dict[str, Any], screening_cfg: Dict[str, Any]):
        self.ma_length = int(indicators_cfg.get("ma_length", 50))
        self.rsi_length = int(indicators_cfg.get("rsi_length", 14))
        _ = screening_cfg

    async def extract_for_symbol(
        self, page: Page, symbol: str, timeframe: str
    ) -> Dict[str, Any]:
        _ = timeframe
        # Try common data window labels.
        rsi = await self._try_extract_value(page, patterns=[f"RSI({self.rsi_length})", "RSI"], prefer_last_float=True)
        ma = await self._try_extract_value(
            page,
            patterns=[f"{self.ma_length}MA", f"SMA{self.ma_length}", f"MA {self.ma_length}"],
            prefer_last_float=True,
        )
        price = await self._try_extract_value(
            page,
            patterns=["Close", "Last", "Price"],
            prefer_last_float=False,
        )

        return {
            "symbol": symbol,
            "price": price,
            "ma50": ma,
            "rsi14": rsi,
            "raw": {
                "ma_patterns": [f"{self.ma_length}MA", f"SMA{self.ma_length}", f"MA {self.ma_length}"],
                "rsi_patterns": [f"RSI({self.rsi_length})", "RSI"],
                "price_patterns": ["Close", "Last", "Price"],
            },
        }

    async def _try_extract_value(
        self, page: Page, patterns: list[str], prefer_last_float: bool
    ) -> Optional[float]:
        for p in patterns:
            try:
                loc = page.locator(f"text={p}").first
                if await loc.count() == 0:
                    continue

                txt = (await loc.inner_text(timeout=1500)).strip()
                # Some labels might include multiple numbers; pick one deterministically.
                floats = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", txt.replace(",", "")) if x not in {"", "+", "-"}]
                if not floats:
                    val = _parse_first_float(txt)
                    if val is not None:
                        return val
                    continue
                return floats[-1] if prefer_last_float else floats[0]
            except Exception:
                continue
        return None

