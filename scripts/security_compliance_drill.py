#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.security_drill import evaluate_security_drill


def _load_json(path: str) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("audit json must be a list")
    normalized: list[dict] = []
    for item in payload:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Run security compliance drill against audit logs.")
    parser.add_argument("--audit-json", required=True, help="path to audit logs json array")
    args = parser.parse_args()

    logs = _load_json(args.audit_json)
    result = evaluate_security_drill(audit_logs=logs)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
