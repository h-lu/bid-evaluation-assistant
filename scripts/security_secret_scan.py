#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.security_scan import scan_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for leaked secrets.")
    parser.add_argument("paths", nargs="*", default=["app", "tests", "docs", "scripts"])
    args = parser.parse_args()
    findings = scan_paths(list(args.paths))
    print(
        json.dumps(
            {
                "success": len(findings) == 0,
                "finding_count": len(findings),
                "findings": findings[:100],
            },
            ensure_ascii=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
