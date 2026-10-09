from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass(frozen=True)
class AppConfig:
    mode: str
    interval_seconds: int
    headless: bool
    screenshot_on_failure: bool
    stop_file: str


@dataclass(frozen=True)
class TradingViewConfig:
    base_url: str
    symbol_prefix: str
    timeframe: str
    paper_trading: bool
    user_data_dir: str
    # Map bare symbol (e.g. XAUUSD) -> full TradingView symbol (e.g. OANDA:XAUUSD).
    symbol_overrides: Dict[str, str]


@dataclass(frozen=True)
class AnalysisConfig:
    watchlist: List[str]
    indicators: Dict[str, Any]
    screening: Dict[str, Any]


@dataclass(frozen=True)
class RiskConfig:
    max_concurrent_positions: int
    max_trades_per_day: int
    max_daily_loss_fraction: float
    cooldown_seconds: int


@dataclass(frozen=True)
class ExecutionConfig:
    quantity: float
    min_signal_score: float


@dataclass(frozen=True)
class BrokerConfig:
    backend: str  # "tradingview_ui" | "mt5"


@dataclass(frozen=True)
class MT5Config:
    enabled: bool
    terminal_path: str
    login_env: str
    password_env: str
    server_env: str
    lot: float
    deviation: int
    magic: int
    dry_run: bool
    symbol_map: Dict[str, str]


@dataclass(frozen=True)
class ScalpingConfig:
    enabled: bool
    chart_timeframe: str
    interval_seconds: int
    sl_points: float
    tp_rr: Tuple[float, float, float, float]
    screening: Dict[str, Any]


@dataclass(frozen=True)
class DashboardConfig:
    enabled: bool
    host: str
    port: int


@dataclass(frozen=True)
class StateConfig:
    sqlite_path: str
    screenshots_dir: str


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    tradingview: TradingViewConfig
    analysis: AnalysisConfig
    risk: RiskConfig
    broker: BrokerConfig
    mt5: MT5Config
    execution: ExecutionConfig
    scalping: ScalpingConfig
    dashboard: DashboardConfig
    state: StateConfig


def load_settings(settings_path: str) -> Settings:
    path = Path(settings_path)
    if not path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    _load_dotenv(path.parents[1] / ".env")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    # Optional local overrides (e.g. saved from the dashboard).
    overrides_path = path.parent / "overrides.yaml"
    if overrides_path.exists():
        raw = _deep_merge(raw, yaml.safe_load(overrides_path.read_text(encoding="utf-8")) or {})

    # Light env overrides (keeps this bot config-driven).
    raw["app"]["mode"] = _env("BOT_MODE", raw["app"].get("mode", "run"))
    if _env("BOT_INTERVAL_SECONDS") is not None:
        raw["app"]["interval_seconds"] = int(_env("BOT_INTERVAL_SECONDS"))  # type: ignore[arg-type]
    if _env("BOT_HEADLESS") is not None:
        raw["app"]["headless"] = _env("BOT_HEADLESS", "false").lower() == "true"

    app = AppConfig(
        mode=raw["app"]["mode"],
        interval_seconds=int(raw["app"]["interval_seconds"]),
        headless=bool(raw["app"]["headless"]),
        screenshot_on_failure=bool(raw["app"].get("screenshot_on_failure", True)),
        stop_file=raw["app"]["stop_file"],
    )

    tv_raw = raw["tradingview"]
    symbol_overrides = dict(tv_raw.get("symbol_overrides") or {})

    tradingview = TradingViewConfig(
        base_url=str(tv_raw["base_url"]),
        symbol_prefix=str(tv_raw["symbol_prefix"]),
        timeframe=str(tv_raw["timeframe"]),
        paper_trading=bool(tv_raw["paper_trading"]),
        user_data_dir=str(tv_raw.get("user_data_dir", "")),
        symbol_overrides=symbol_overrides,
    )

    analysis = AnalysisConfig(
        watchlist=list(raw["analysis"]["watchlist"]),
        indicators=dict(raw["analysis"]["indicators"]),
        screening=dict(raw["analysis"]["screening"]),
    )

    risk = RiskConfig(
        max_concurrent_positions=int(raw["risk"]["max_concurrent_positions"]),
        max_trades_per_day=int(raw["risk"]["max_trades_per_day"]),
        max_daily_loss_fraction=float(raw["risk"]["max_daily_loss_fraction"]),
        cooldown_seconds=int(raw["risk"]["cooldown_seconds"]),
    )

    execution = ExecutionConfig(
        quantity=float(raw["execution"]["quantity"]),
        min_signal_score=float(raw["execution"]["min_signal_score"]),
    )

    broker_raw = raw.get("broker") or {}
    broker = BrokerConfig(
        backend=str(broker_raw.get("backend", "tradingview_ui")),
    )

    mt5_raw = raw.get("mt5") or {}
    mt5 = MT5Config(
        enabled=bool(mt5_raw.get("enabled", False)),
        terminal_path=str(mt5_raw.get("terminal_path", "")),
        login_env=str(mt5_raw.get("login_env", "MT5_LOGIN")),
        password_env=str(mt5_raw.get("password_env", "MT5_PASSWORD")),
        server_env=str(mt5_raw.get("server_env", "MT5_SERVER")),
        lot=float(mt5_raw.get("lot", 0.01)),
        deviation=int(mt5_raw.get("deviation", 20)),
        magic=int(mt5_raw.get("magic", 9001)),
        dry_run=bool(mt5_raw.get("dry_run", True)),
        symbol_map=dict(mt5_raw.get("symbol_map") or {}),
    )

    sp = raw.get("scalping") or {}
    tp_rr_list = sp.get("tp_rr") or [1.0, 2.0, 3.0, 4.0]
    if len(tp_rr_list) != 4:
        raise ValueError("scalping.tp_rr must have exactly 4 values (TP1..TP4)")
    tp_rr = (float(tp_rr_list[0]), float(tp_rr_list[1]), float(tp_rr_list[2]), float(tp_rr_list[3]))

    scalping = ScalpingConfig(
        enabled=bool(sp.get("enabled", False)),
        chart_timeframe=str(sp.get("chart_timeframe", raw["tradingview"]["timeframe"])),
        interval_seconds=int(sp.get("interval_seconds", raw["app"]["interval_seconds"])),
        sl_points=float(sp.get("sl_points", 5.0)),
        tp_rr=tp_rr,
        screening=dict(sp.get("screening") or {}),
    )

    dash = raw.get("dashboard") or {}
    dashboard = DashboardConfig(
        enabled=bool(dash.get("enabled", True)),
        host=str(dash.get("host", "127.0.0.1")),
        port=int(dash.get("port", 8765)),
    )

    state = StateConfig(
        sqlite_path=str(raw["state"]["sqlite_path"]),
        screenshots_dir=str(raw["state"]["screenshots_dir"]),
    )

    return Settings(
        app=app,
        tradingview=tradingview,
        analysis=analysis,
        risk=risk,
        broker=broker,
        mt5=mt5,
        execution=execution,
        scalping=scalping,
        dashboard=dashboard,
        state=state,
    )

