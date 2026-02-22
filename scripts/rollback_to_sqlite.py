#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.backend_rollback import update_dotenv_for_sqlite


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch backend env settings to sqlite rollback mode")
    parser.add_argument("--env-file", default=".env.local", help="dotenv file path")
    parser.add_argument("--dry-run", action="store_true", help="print updated content without writing file")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    old_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    new_content = update_dotenv_for_sqlite(old_content)

    if not args.dry_run:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(new_content, encoding="utf-8")

    summary = {
        "env_file": str(env_path),
        "dry_run": bool(args.dry_run),
        "store_backend": "sqlite",
        "queue_backend": "sqlite",
        "verify_commands": [
            "pytest -q tests/test_store_persistence_backend.py",
            "pytest -q tests/test_queue_backend.py",
            "pytest -q tests/test_internal_outbox_queue_api.py tests/test_worker_drain_api.py",
        ],
    }
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
