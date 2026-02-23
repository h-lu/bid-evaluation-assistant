from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


def _import_psycopg() -> Any:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL backends; install psycopg[binary]") from exc
    return psycopg


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


def _canonical_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return blob


def _size_of(value: Any) -> int:
    if isinstance(value, dict | list):
        return len(value)
    return 0 if value is None else 1


def compare_store_payloads(
    sqlite_payload: dict[str, Any],
    postgres_payload: dict[str, Any],
    *,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    keys = sections or [
        "jobs",
        "documents",
        "document_chunks",
        "projects",
        "suppliers",
        "rule_packs",
        "evaluation_reports",
        "parse_manifests",
        "workflow_checkpoints",
        "dlq_items",
        "audit_logs",
        "domain_events_outbox",
        "outbox_delivery_records",
    ]
    rows: list[dict[str, Any]] = []
    mismatch: list[str] = []
    for key in keys:
        left = sqlite_payload.get(key)
        right = postgres_payload.get(key)
        left_hash = _canonical_hash(left)
        right_hash = _canonical_hash(right)
        matched = left_hash == right_hash
        if not matched:
            mismatch.append(key)
        rows.append(
            {
                "section": key,
                "matched": matched,
                "sqlite_count": _size_of(left),
                "postgres_count": _size_of(right),
                "sqlite_hash": left_hash,
                "postgres_hash": right_hash,
            }
        )
    return {
        "all_matched": len(mismatch) == 0,
        "mismatch_sections": mismatch,
        "sections": rows,
    }


def load_sqlite_store_payload(sqlite_path: str) -> dict[str, Any]:
    path = Path(sqlite_path)
    if not path.exists():
        raise FileNotFoundError(f"sqlite db not found: {path}")
    with sqlite3.connect(str(path)) as conn:
        row = conn.execute("SELECT payload FROM store_state WHERE id = 1").fetchone()
    if row is None or not isinstance(row[0], str):
        return {}
    payload = json.loads(row[0])
    return payload if isinstance(payload, dict) else {}


def load_postgres_store_payload(*, dsn: str, table_name: str = "bea_store_state") -> dict[str, Any]:
    table = _validate_identifier(table_name)
    psycopg = _import_psycopg()
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT payload::text FROM {table} WHERE id = 1")
        row = cur.fetchone()
    if row is None or not isinstance(row[0], str):
        return {}
    payload = json.loads(row[0])
    return payload if isinstance(payload, dict) else {}
