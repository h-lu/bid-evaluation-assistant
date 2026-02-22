#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from app.main import queue_backend
from app.store import store
from app.worker_runtime import create_worker_runtime_from_env


def main() -> int:
    parser = argparse.ArgumentParser(description="Run resident worker loop for queued jobs.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=0,
        help="Stop after N iterations (0 means run forever).",
    )
    args = parser.parse_args()

    runtime = create_worker_runtime_from_env(store=store, queue_backend=queue_backend)
    if args.iterations > 0:
        stats = runtime.run_forever(stop_after_iterations=args.iterations)
    else:
        stats = runtime.run_forever(stop_after_iterations=None)
    print(json.dumps({"success": True, "stats": stats}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
