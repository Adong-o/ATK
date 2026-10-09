from __future__ import annotations

import argparse
import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .browser.controller import BrowserController
from .config import Settings, load_settings
from .execution.mt5_terminal import MT5TerminalExecutor
from .execution.tradingview_ui import TradingViewUITradeExecutor
from .signals.screening_rules import ScreeningRules
from .scalping.plan import build_bracket_plan, plan_to_dict
from .state.db import StateDB
from .state.portfolio import PaperPortfolio
from .utils.logger import log_error, log_info, setup_logger
from .risk.manager import RiskManager
from .browser.extractors import ChartDataExtractor


def _project_root() -> Path:
    # src/main.py -> bot/src -> bot
    return Path(__file__).resolve().parents[1]


def _stop_requested(stop_file_path: Path) -> bool:
    return stop_file_path.exists()


def _write_live_status(root: Path, payload: Dict[str, Any]) -> None:
    out = root / "runs" / "live_status.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


async def run_loop(settings: Settings, run_once: bool) -> None:
    root = _project_root()
    stop_file = root / settings.app.stop_file

    runs_dir = root / "runs"
    log_dir = str(runs_dir / "logs")
    logger = setup_logger(log_dir)

    if settings.dashboard.enabled:
        from .dashboard.server import serve_dashboard

        t = threading.Thread(
            target=serve_dashboard,
            kwargs={
                "host": settings.dashboard.host,
                "port": settings.dashboard.port,
                "project_root": root,
            },
            daemon=True,
        )
        t.start()
        log_info(
            logger,
            "Dashboard listening (save SL/TP + scalping settings here)",
            url=f"http://{settings.dashboard.host}:{settings.dashboard.port}/",
        )

    db = StateDB(str(root / settings.state.sqlite_path))
    portfolio = PaperPortfolio()  # MVP placeholder; later can track PnL

    browser = BrowserController(tv_cfg=settings.tradingview, headless=settings.app.headless)
    await browser.start()

    screening_cfg = dict(settings.analysis.screening)
    if settings.scalping.enabled:
        screening_cfg.update(settings.scalping.screening)

    extractor = ChartDataExtractor(
        indicators_cfg=settings.analysis.indicators,
        screening_cfg=screening_cfg,
    )
    screening = ScreeningRules(screening_cfg=screening_cfg)
    risk = RiskManager(risk_cfg=settings.risk)
    tv_executor = TradingViewUITradeExecutor(
        tv_cfg=settings.tradingview,
        quantity=settings.execution.quantity,
        min_signal_score=settings.execution.min_signal_score,
    )
    mt5_executor: Optional[MT5TerminalExecutor] = None
    if settings.broker.backend == "mt5":
        if not settings.mt5.enabled:
            raise RuntimeError("broker.backend is mt5 but mt5.enabled is false in settings.")
        mt5_executor = MT5TerminalExecutor(
            mt5_cfg=settings.mt5,
            min_signal_score=settings.execution.min_signal_score,
            risk_cfg=settings.risk,
        )
        await mt5_executor.initialize()

    symbols = list(settings.analysis.watchlist)
    chart_timeframe = (
        settings.scalping.chart_timeframe
        if settings.scalping.enabled
        else settings.tradingview.timeframe
    )
    loop_interval = (
        settings.scalping.interval_seconds
        if settings.scalping.enabled
        else settings.app.interval_seconds
    )

    try:
        while True:
            if _stop_requested(stop_file):
                log_info(logger, "Stop file detected. Exiting.")
                break

            run_id = db.create_run(
                mode="run",
                payload={
                    "symbols": symbols,
                    "timeframe": chart_timeframe,
                    "scalping": settings.scalping.enabled,
                },
            )
            log_info(logger, "Starting screening run", run_id=run_id, symbols=len(symbols))

            for symbol in symbols:
                if _stop_requested(stop_file):
                    break

                try:
                    await browser.navigate_to_symbol(
                        symbol=symbol,
                        timeframe=chart_timeframe,
                        paper_trading=settings.tradingview.paper_trading,
                    )

                    indicator_values = await extractor.extract_for_symbol(
                        page=await browser.get_page(),
                        symbol=symbol,
                        timeframe=chart_timeframe,
                    )
                    # Keep a fresh screenshot so dashboard can show live chart progress.
                    live_shot = root / settings.state.screenshots_dir / f"live_{symbol}.png"
                    try:
                        await browser.screenshot(str(live_shot))
                    except Exception:
                        pass

                    decision = screening.decide(indicator_values)
                    live_payload: Dict[str, Any] = {
                        "run_id": run_id,
                        "symbol": symbol,
                        "timeframe": chart_timeframe,
                        "indicators": indicator_values,
                        "decision": decision,
                        "bracket": None,
                        "order_result": None,
                        "screenshot": str(live_shot),
                    }
                    if decision["action"] == "skip":
                        _write_live_status(root, live_payload)
                        db.record_execution(
                            run_id=run_id,
                            symbol=symbol,
                            side="none",
                            action="skip",
                            score=decision.get("score"),
                            success=True,
                            error=None,
                            details=decision,
                        )
                        continue

                    allowed, reason = risk.can_trade(
                        symbol=symbol,
                        side=decision["side"],
                        score=decision["score"],
                    )
                    if not allowed:
                        log_info(logger, "Risk manager blocked trade", symbol=symbol, reason=reason)
                        db.record_execution(
                            run_id=run_id,
                            symbol=symbol,
                            side=decision["side"],
                            action="blocked",
                            score=decision.get("score"),
                            success=False,
                            error=reason,
                            details=decision,
                        )
                        continue

                    bracket: Optional[Dict[str, Any]] = None
                    if settings.scalping.enabled:
                        entry_px = indicator_values.get("price")
                        if entry_px is None:
                            db.record_execution(
                                run_id=run_id,
                                symbol=symbol,
                                side=decision["side"],
                                action="skip",
                                score=decision.get("score"),
                                success=True,
                                error="no_price_for_bracket",
                                details=decision,
                            )
                            continue
                        plan = build_bracket_plan(
                            float(entry_px),
                            decision["side"],
                            settings.scalping.sl_points,
                            settings.scalping.tp_rr,
                        )
                        bracket = plan_to_dict(plan)
                        live_payload["bracket"] = bracket
                        log_info(logger, "Bracket plan", symbol=symbol, bracket=bracket)

                    if settings.broker.backend == "mt5" and mt5_executor is not None:
                        order_result = await mt5_executor.place_order(
                            symbol=symbol,
                            side=decision["side"],
                            score=decision["score"],
                            bracket=bracket,
                        )
                    else:
                        order_result = await tv_executor.place_paper_order(
                            page=await browser.get_page(),
                            symbol=symbol,
                            side=decision["side"],
                            score=decision["score"],
                            bracket=bracket,
                        )
                    live_payload["order_result"] = order_result
                    _write_live_status(root, live_payload)
                    risk.record_trade_attempt(success=order_result["success"])
                    portfolio.apply_execution_stub(order_result)

                    db.record_execution(
                        run_id=run_id,
                        symbol=symbol,
                        side=decision["side"],
                        action="trade",
                        score=decision.get("score"),
                        success=order_result["success"],
                        error=order_result.get("error"),
                        details={
                            "decision": decision,
                            "order_result": order_result,
                            "bracket": bracket,
                        },
                    )

                except Exception as e:
                    err = str(e)
                    log_error(logger, "Symbol run failed", symbol=symbol, error=err)
                    # Best-effort screenshot for debugging.
                    if settings.app.screenshot_on_failure:
                        ts = __import__("datetime").datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                        out = root / settings.state.screenshots_dir / f"fail_{symbol}_{ts}.png"
                        try:
                            await browser.screenshot(str(out))
                        except Exception:
                            pass
                    db.record_execution(
                        run_id=run_id,
                        symbol=symbol,
                        side="none",
                        action="error",
                        score=None,
                        success=False,
                        error=err,
                        details=None,
                    )

            if run_once:
                break

            log_info(logger, "Run complete. Sleeping until next interval.")
            await asyncio.sleep(loop_interval)

    finally:
        if mt5_executor is not None:
            await mt5_executor.shutdown()
        await browser.close()


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--settings",
        default=str(_project_root() / "config" / "settings.yaml"),
        help="Path to settings.yaml",
    )
    parser.add_argument("--run-once", action="store_true", help="Run one screening/execution loop")
    args = parser.parse_args()

    settings = load_settings(args.settings)

    if settings.app.mode == "run":
        await run_loop(settings, run_once=args.run_once)
    elif settings.app.mode == "webhook":
        from .alerts.webhook_receiver import run_webhook_receiver

        await run_webhook_receiver(settings)
    else:
        raise ValueError(f"Unknown mode: {settings.app.mode}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

