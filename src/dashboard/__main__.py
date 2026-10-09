from __future__ import annotations

import argparse
from pathlib import Path

from .server import serve_dashboard


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    serve_dashboard(args.host, args.port, root)


if __name__ == "__main__":
    main()
