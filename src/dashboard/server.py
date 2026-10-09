from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs


def _html_form(overrides: Dict[str, Any]) -> bytes:
    sp = overrides.get("scalping") or {}
    ex = overrides.get("execution") or {}
    tv = overrides.get("tradingview") or {}
    tp_rr = sp.get("tp_rr") or [1.0, 2.0, 3.0, 4.0]

    def gv(key: str, default: str = "") -> str:
        v = sp.get(key)
        if v is None:
            return default
        return str(v)

    en = sp.get("enabled", True)
    enabled_str = "true" if bool(en) else "false"

    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Bot controls</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 24px auto; }}
label {{ display: block; margin: 10px 0 4px; }}
input {{ width: 100%; padding: 8px; box-sizing: border-box; }}
button {{ margin-top: 16px; padding: 10px 16px; }}
.note {{ color: #444; font-size: 14px; margin-top: 24px; }}
code {{ background: #f4f4f4; padding: 2px 6px; }}
.panel {{ border: 1px solid #ddd; border-radius: 10px; padding: 12px; margin-bottom: 18px; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; white-space: pre-wrap; }}
img {{ max-width: 100%; border-radius: 8px; border: 1px solid #ddd; }}
</style></head><body>
<h1>Trading bot parameters</h1>
<p>Edit values and save. They are written to <code>config/overrides.yaml</code> (merged on next bot start).</p>
<div class="panel">
  <h2>Live scalping view (auto-refresh)</h2>
  <p id="liveTitle">Waiting for live status...</p>
  <img id="liveImg" alt="live chart screenshot">
  <div class="mono" id="liveMeta"></div>
</div>
<form method="post" action="/save">
  <h2>Scalping</h2>
  <label>Enabled (true/false)</label>
  <input name="scalping.enabled" value="{enabled_str}">

  <label>Chart timeframe (minutes as string, e.g. 5 or 1)</label>
  <input name="scalping.chart_timeframe" value="{gv('chart_timeframe','5')}">

  <label>Loop interval (seconds)</label>
  <input name="scalping.interval_seconds" value="{gv('interval_seconds','120')}">

  <label>Stop distance (price units — tune for XAUUSD vs FX)</label>
  <input name="scalping.sl_points" value="{gv('sl_points','5')}">

  <label>TP1 RR (multiple of SL distance)</label>
  <input name="tp_rr0" value="{tp_rr[0]}">
  <label>TP2 RR</label>
  <input name="tp_rr1" value="{tp_rr[1]}">
  <label>TP3 RR</label>
  <input name="tp_rr2" value="{tp_rr[2]}">
  <label>TP4 RR</label>
  <input name="tp_rr3" value="{tp_rr[3]}">

  <h2>Execution</h2>
  <label>Order size (quantity / units)</label>
  <input name="execution.quantity" value="{ex.get('quantity','')}">

  <label>Min signal score</label>
  <input name="execution.min_signal_score" value="{ex.get('min_signal_score','')}">

  <h2>Symbol override (XAUUSD)</h2>
  <label>Full TradingView symbol for XAUUSD (example: OANDA:XAUUSD)</label>
  <input name="tradingview.symbol_overrides.XAUUSD" value="{tv.get('symbol_overrides', {}).get('XAUUSD','')}">

  <button type="submit">Save overrides</button>
</form>
<p class="note">Risk: automated trading can lose money. TP2–TP4 may not appear in every TradingView order panel; the bot still computes all four prices and tries to fill visible fields.</p>
<script>
async function refreshLive() {{
  try {{
    const r = await fetch('/status');
    if (!r.ok) return;
    const d = await r.json();
    document.getElementById('liveTitle').textContent = `Symbol: ${{d.symbol || '-'}} | TF: ${{d.timeframe || '-'}}`;
    document.getElementById('liveMeta').textContent = JSON.stringify({{
      indicators: d.indicators,
      decision: d.decision,
      bracket: d.bracket,
      order_result: d.order_result
    }}, null, 2);
    if (d.symbol) {{
      document.getElementById('liveImg').src = `/image?symbol=${{encodeURIComponent(d.symbol)}}&t=${{Date.now()}}`;
    }}
  }} catch (e) {{}}
}}
setInterval(refreshLive, 2500);
refreshLive();
</script>
</body></html>"""
    return body.encode("utf-8")


def _load_overrides(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _save_overrides(path: Path, data: Dict[str, Any]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def serve_dashboard(host: str, port: int, project_root: Path) -> None:
    overrides_path = project_root / "config" / "overrides.yaml"
    status_path = project_root / "runs" / "live_status.json"
    shots_dir = project_root / "runs" / "screenshots"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/status"):
                if not status_path.exists():
                    body = b'{"status":"waiting"}'
                else:
                    body = status_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path.startswith("/image"):
                qs = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                symbol = (qs.get("symbol") or [""])[0].strip().upper()
                if not symbol:
                    self.send_error(400)
                    return
                img = shots_dir / f"live_{symbol}.png"
                if not img.exists():
                    self.send_error(404)
                    return
                body = img.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path != "/" and not self.path.startswith("/?"):
                self.send_error(404)
                return
            data = _load_overrides(overrides_path)
            payload = _html_form(data)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            if self.path != "/save":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            form = parse_qs(raw, keep_blank_values=True)

            def one(key: str) -> str:
                vals = form.get(key)
                return vals[0] if vals else ""

            merged: Dict[str, Any] = _load_overrides(overrides_path)
            merged.setdefault("scalping", {})
            merged.setdefault("execution", {})
            merged.setdefault("tradingview", {})
            merged["tradingview"].setdefault("symbol_overrides", {})

            if one("scalping.enabled").lower() in ("true", "1", "yes"):
                merged["scalping"]["enabled"] = True
            elif one("scalping.enabled").lower() in ("false", "0", "no"):
                merged["scalping"]["enabled"] = False

            def try_float(key: str, dest: str) -> None:
                s = one(key).strip()
                if s == "":
                    return
                merged["scalping"][dest] = float(s)

            def try_int(key: str, dest: str) -> None:
                s = one(key).strip()
                if s == "":
                    return
                merged["scalping"][dest] = int(s)

            s = one("scalping.chart_timeframe").strip()
            if s:
                merged["scalping"]["chart_timeframe"] = s
            try_int("scalping.interval_seconds", "interval_seconds")
            try_float("scalping.sl_points", "sl_points")

            rr = []
            for i in range(4):
                key = f"tp_rr{i}"
                s = one(key).strip()
                if s:
                    rr.append(float(s))
            if len(rr) == 4:
                merged["scalping"]["tp_rr"] = rr

            q = one("execution.quantity").strip()
            if q:
                merged["execution"]["quantity"] = float(q)
            ms = one("execution.min_signal_score").strip()
            if ms:
                merged["execution"]["min_signal_score"] = float(ms)

            sym = one("tradingview.symbol_overrides.XAUUSD").strip()
            if sym:
                merged["tradingview"]["symbol_overrides"]["XAUUSD"] = sym

            _save_overrides(overrides_path, merged)

            body = b'{"ok":true,"saved":"config/overrides.yaml"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = HTTPServer((host, port), Handler)
    server.serve_forever()
