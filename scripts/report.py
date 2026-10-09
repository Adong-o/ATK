from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.state.db import StateDB


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parents[1] / "runs" / "state.db"),
        help="Path to SQLite state.db",
    )
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    db = StateDB(args.db)
    rows = db.fetch_summary(limit=args.limit)

    total = len(rows)
    success = sum(1 for r in rows if r["success"])
    failure = total - success
    success_rate = (success / total * 100.0) if total else 0.0

    by_action = Counter(r["action"] for r in rows)
    by_symbol = Counter(r["symbol"] for r in rows)

    worst = sorted((r for r in rows if not r["success"]), key=lambda r: str(r.get("error") or ""), reverse=True)

    summary: Dict[str, Any] = {
        "total_attempts": total,
        "success": success,
        "failure": failure,
        "success_rate_percent": round(success_rate, 2),
        "by_action": dict(by_action),
        "by_symbol_top": by_symbol.most_common(10),
    }

    print(json.dumps(summary, indent=2))
    if failure and worst:
        print("\nSample failures:")
        for r in worst[:10]:
            print(f"- {r['ts_utc']} {r['symbol']} {r['side']} {r['action']} error={r['error']}")


if __name__ == "__main__":
    main()

