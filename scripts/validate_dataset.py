#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate


def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_samples(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if raw[0] == "[":
        return json.loads(raw)
    samples: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        samples.append(json.loads(line))
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate eval dataset samples against schema.")
    parser.add_argument("--input", required=True, help="Dataset JSON or JSONL file.")
    parser.add_argument(
        "--schema",
        default="docs/datasets/eval-dataset-schema.json",
        help="Schema file path.",
    )
    args = parser.parse_args()

    schema_path = Path(args.schema)
    input_path = Path(args.input)
    schema = load_schema(schema_path)
    samples = iter_samples(input_path)

    failures = 0
    for idx, sample in enumerate(samples):
        try:
            validate(instance=sample, schema=schema)
        except ValidationError as exc:
            failures += 1
            print(f"[invalid] index={idx} error={exc.message}")
    if failures:
        print(f"validation_failed count={failures}")
        return 1
    print(f"validation_ok count={len(samples)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
