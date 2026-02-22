#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.slo_probe import evaluate_latency_slo, summarize_http_probe


def _single_request(
    *,
    url: str,
    timeout_s: float,
    method: str,
    body: bytes | None,
    headers: dict[str, str],
) -> tuple[float, int]:
    started = time.perf_counter()
    req = request.Request(url=url, method=method, data=body, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            status = int(resp.getcode())
    except HTTPError as exc:
        status = int(exc.code)
    except URLError:
        status = 599
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms, status


def _parse_headers(header_args: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in header_args:
        if ":" not in item:
            raise ValueError(f"invalid header: {item}")
        key, value = item.split(":", maxsplit=1)
        headers[key.strip()] = value.strip()
    return headers


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SLO probe against an HTTP endpoint.")
    parser.add_argument("--url", required=True, help="target URL")
    parser.add_argument("--requests", type=int, default=50, help="number of requests")
    parser.add_argument("--concurrency", type=int, default=10, help="parallel workers")
    parser.add_argument("--timeout-s", type=float, default=5.0, help="HTTP timeout in seconds")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--header", action="append", default=[], help="HTTP header, key:value")
    parser.add_argument("--json-body", default="", help="request json payload")
    parser.add_argument("--p95-limit-ms", type=float, default=1500.0, help="p95 SLO limit")
    parser.add_argument("--error-rate-limit", type=float, default=0.01, help="error-rate SLO limit")
    args = parser.parse_args()

    headers = _parse_headers(args.header)
    body = args.json_body.encode("utf-8") if args.json_body else None
    if body is not None and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    latencies: list[float] = []
    status_codes: list[int] = []

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = [
            executor.submit(
                _single_request,
                url=args.url,
                timeout_s=args.timeout_s,
                method=args.method.upper(),
                body=body,
                headers=headers,
            )
            for _ in range(max(1, args.requests))
        ]
        for fut in as_completed(futures):
            latency_ms, status = fut.result()
            latencies.append(latency_ms)
            status_codes.append(status)

    summary = summarize_http_probe(latencies_ms=latencies, status_codes=status_codes)
    gate = evaluate_latency_slo(
        summary=summary,
        p95_limit_ms=float(args.p95_limit_ms),
        error_rate_limit=float(args.error_rate_limit),
    )
    report: dict[str, Any] = {
        "url": args.url,
        "requests": max(1, args.requests),
        "concurrency": max(1, args.concurrency),
        "summary": summary,
        "gate": gate,
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if gate["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
