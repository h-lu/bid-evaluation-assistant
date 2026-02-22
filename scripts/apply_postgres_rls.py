#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.rls import PostgresRlsManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply PostgreSQL tenant RLS policies on core tables")
    parser.add_argument("--dsn", default=os.getenv("POSTGRES_DSN", ""), help="PostgreSQL DSN")
    parser.add_argument(
        "--tables",
        default="",
        help="comma-separated table names; default uses built-in core tables",
    )
    args = parser.parse_args()

    dsn = str(args.dsn or "").strip()
    if not dsn:
        raise SystemExit("POSTGRES_DSN is required (pass --dsn or set env)")

    tables: list[str] | None = None
    if args.tables.strip():
        tables = [x.strip() for x in args.tables.split(",") if x.strip()]

    manager = PostgresRlsManager(dsn, tables=tables)
    applied = manager.apply()
    print(json.dumps({"applied_tables": applied, "count": len(applied)}, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
