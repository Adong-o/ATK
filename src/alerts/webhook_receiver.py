from __future__ import annotations

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..config import Settings
from ..risk.manager import RiskManager
from ..state.db import StateDB
from ..state.portfolio import PaperPortfolio
from ..utils.logger import log_error, log_info, setup_logger


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


async def run_webhook_receiver(settings: Settings) -> None:
    root = _project_root()
    runs_dir = root / "runs"
    logger = setup_logger(str(runs_dir / "logs"))
    db = StateDB(str(root / settings.state.sqlite_path))
    risk = RiskManager(risk_cfg=settings.risk)
    portfolio = PaperPortfolio()

    stop_file = root / settings.app.stop_file
    port = int(os.environ.get("BOT_WEBHOOK_PORT", "8000"))
    bind = os.environ.get("BOT_WEBHOOK_BIND", "0.0.0.0")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: Dict[str, Any]) -> None:
            payload = json.dumps(body, ensure_ascii=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length > 0 else ""
                data = json.loads(raw) if raw else {}
            except Exception:
                self._send(400, {"ok": False, "error": "invalid_json"})
                return

            symbol = str(data.get("symbol", "")).upper().strip()
            side = str(data.get("side", "")).lower().strip()
            score = data.get("score", None)

            if not symbol or side not in {"long", "short"}:
                self._send(400, {"ok": False, "error": "missing_or_invalid_fields"})
                return

            allowed, reason = risk.can_trade(symbol=symbol, side=side, score=score)
            if not allowed:
                run_id = db.create_run(
                    mode="webhook_signal",
                    payload={"symbol": symbol, "side": side, "score": score, "blocked_reason": reason},
                )
                db.record_execution(
                    run_id=run_id,
                    symbol=symbol,
                    side=side,
                    action="blocked",
                    score=score if isinstance(score, (int, float)) else None,
                    success=False,
                    error=reason,
                    details=data,
                )
                self._send(200, {"ok": False, "blocked": True, "reason": reason})
                return

            # MVP fallback: no UI execution here; we record the intent and track as if it "opened".
            run_id = db.create_run(
                mode="webhook_signal",
                payload={"symbol": symbol, "side": side, "score": score},
            )
            order_result = {"success": True, "source": "webhook", "symbol": symbol, "side": side}
            risk.record_trade_attempt(success=True)
            portfolio.apply_execution_stub(order_result)
            db.record_execution(
                run_id=run_id,
                symbol=symbol,
                side=side,
                action="trade_intent",
                score=score if isinstance(score, (int, float)) else None,
                success=True,
                error=None,
                details={"source": "webhook", "raw": data},
            )
            self._send(200, {"ok": True})

        def log_message(self, format: str, *args: Any) -> None:
            # Silence default HTTP logging; we use structured logs instead.
            return

    server = HTTPServer((bind, port), Handler)
    server.timeout = 1.0  # so we can check stop_file periodically

    log_info(logger, "Webhook receiver started", bind=bind, port=port)
    try:
        while True:
            if stop_file.exists():
                log_info(logger, "Stop file detected. Stopping webhook receiver.")
                break
            server.handle_request()
            await asyncio.sleep(0)
    finally:
        server.server_close()

