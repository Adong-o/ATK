from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateDB:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts_utc TEXT NOT NULL,
              mode TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id INTEGER NOT NULL,
              ts_utc TEXT NOT NULL,
              symbol TEXT NOT NULL,
              side TEXT NOT NULL,
              action TEXT NOT NULL,
              score REAL,
              success INTEGER NOT NULL,
              error TEXT,
              details_json TEXT,
              FOREIGN KEY(run_id) REFERENCES runs(id)
            )
            """
        )
        self.conn.commit()

    def create_run(self, mode: str, payload: Dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs(ts_utc, mode, payload_json) VALUES(?,?,?)",
            (utc_now_iso(), mode, json.dumps(payload, ensure_ascii=True)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def record_execution(
        self,
        run_id: int,
        symbol: str,
        side: str,
        action: str,
        score: Optional[float],
        success: bool,
        error: Optional[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO executions(run_id, ts_utc, symbol, side, action, score, success, error, details_json)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id,
                utc_now_iso(),
                symbol,
                side,
                action,
                score,
                1 if success else 0,
                error,
                json.dumps(details, ensure_ascii=True) if details is not None else None,
            ),
        )
        self.conn.commit()

    def fetch_summary(self, limit: int = 1000) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT r.ts_utc, r.mode, e.symbol, e.side, e.action, e.score, e.success, e.error
            FROM executions e
            JOIN runs r ON r.id = e.run_id
            ORDER BY e.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "ts_utc": row[0],
                    "mode": row[1],
                    "symbol": row[2],
                    "side": row[3],
                    "action": row[4],
                    "score": row[5],
                    "success": bool(row[6]),
                    "error": row[7],
                }
            )
        return out

