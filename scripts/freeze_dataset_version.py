#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate


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


def checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze dataset version with manifest.")
    parser.add_argument("--input", required=True, help="Dataset JSON or JSONL file.")
    parser.add_argument("--name", required=True, help="Dataset name (e.g. eval-core).")
    parser.add_argument("--version", required=True, help="Dataset version (e.g. v1.0.0).")
    parser.add_argument(
        "--schema",
        default="docs/datasets/eval-dataset-schema.json",
        help="Schema file path.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/datasets",
        help="Output directory.",
    )
    args = parser.parse_args()

    schema = load_schema(Path(args.schema))
    samples = iter_samples(Path(args.input))
    for sample in samples:
        validate(instance=sample, schema=schema)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frozen_name = f"{args.name}-{args.version}.json"
    data_path = out_dir / frozen_name
    payload = json.dumps(samples, ensure_ascii=False, indent=2).encode("utf-8")
    data_path.write_bytes(payload)

    manifest = {
        "dataset_name": args.name,
        "dataset_version": args.version,
        "sample_count": len(samples),
        "checksum_sha256": checksum(payload),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = out_dir / f"{args.name}-{args.version}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"frozen {data_path} samples={len(samples)}")
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
