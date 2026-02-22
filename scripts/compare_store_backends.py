#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.backend_consistency import compare_store_payloads
from app.ops.backend_consistency import load_postgres_store_payload
from app.ops.backend_consistency import load_sqlite_store_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare sqlite/postgres store payload consistency")
    parser.add_argument("--sqlite-path", required=True, help="sqlite store db path")
    parser.add_argument("--postgres-dsn", required=True, help="postgres dsn")
    parser.add_argument("--postgres-table", default="bea_store_state", help="postgres state table")
    parser.add_argument("--sections", default="", help="comma-separated section names")
    args = parser.parse_args()

    sections = [x.strip() for x in args.sections.split(",") if x.strip()] if args.sections.strip() else None
    sqlite_payload = load_sqlite_store_payload(args.sqlite_path)
    postgres_payload = load_postgres_store_payload(dsn=args.postgres_dsn, table_name=args.postgres_table)
    result = compare_store_payloads(sqlite_payload, postgres_payload, sections=sections)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if result["all_matched"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
