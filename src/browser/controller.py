from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..config import TradingViewConfig


@dataclass
class BrowserSession:
    playwright: any
    browser: Browser
    context: BrowserContext
    page: Page


class BrowserController:
    def __init__(self, tv_cfg: TradingViewConfig, headless: bool):
        self.tv_cfg = tv_cfg
        self.headless = headless

        self._session: Optional[BrowserSession] = None

    async def start(self) -> None:
        if self._session is not None:
            return

        playwright = await async_playwright().start()
        # NOTE: persistent profiles require launch_persistent_context.
        # For MVP reliability, we use a normal ephemeral context.
        if self.tv_cfg.user_data_dir.strip():
            Path(self.tv_cfg.user_data_dir).resolve().mkdir(parents=True, exist_ok=True)

        browser = await playwright.chromium.launch(headless=self.headless)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        self._session = BrowserSession(
            playwright=playwright, browser=browser, context=context, page=page
        )

    async def close(self) -> None:
        if self._session is None:
            return
        await self._session.context.close()
        await self._session.browser.close()
        await self._session.playwright.stop()
        self._session = None

    async def get_page(self) -> Page:
        if self._session is None:
            raise RuntimeError("Browser session not started. Call start() first.")
        return self._session.page

    def _symbol_to_tv(self, symbol: str) -> str:
        key = symbol.upper().strip()
        if key in self.tv_cfg.symbol_overrides:
            return self.tv_cfg.symbol_overrides[key]
        if symbol.startswith(self.tv_cfg.symbol_prefix):
            return symbol
        return f"{self.tv_cfg.symbol_prefix}{symbol}"

    async def navigate_to_symbol(
        self, symbol: str, timeframe: str, paper_trading: bool
    ) -> None:
        page = await self.get_page()
        tv_symbol = self._symbol_to_tv(symbol)

        # TradingView chart URL format can vary; keep it simple for MVP.
        # We'll rely on in-page controls/menus to adjust timeframe and paper mode.
        url = f"{self.tv_cfg.base_url}/chart/?symbol={quote(tv_symbol, safe='')}"
        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Let chart render; indicator loading can be slow.
                await page.wait_for_timeout(5000 + attempt * 500)
                # Ensure page is interactive.
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass

                # Attempt to set timeframe if TradingView doesn't default to it.
                await self._try_set_timeframe(timeframe, attempts=2)
                last_err = None
                break
            except Exception as e:
                last_err = e
                # Backoff before retry.
                await page.wait_for_timeout(2000 * attempt)

        if last_err is not None:
            raise last_err

        # Paper trading mode: implementation is handled in executor (best-effort).
        _ = paper_trading

    async def _try_set_timeframe(self, timeframe: str, attempts: int = 1) -> None:
        page = await self.get_page()

        # Heuristic: try to find timeframe button group and click matching value.
        # If it fails, we proceed (extractor will validate what we actually read).
        candidates = [f"button:has-text('{timeframe}')", f"text={timeframe}"]
        for _ in range(max(1, attempts)):
            for sel in candidates:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() == 0:
                        continue
                    await loc.click(timeout=2000)
                    await page.wait_for_timeout(1500)
                    return
                except Exception:
                    continue

    async def screenshot(self, out_path: str) -> None:
        page = await self.get_page()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=out_path, full_page=True)

