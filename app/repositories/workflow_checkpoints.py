from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryWorkflowCheckpointsRepository:
    def __init__(self, checkpoints: dict[str, list[dict[str, Any]]]) -> None:
        self._checkpoints = checkpoints

    def append(self, *, checkpoint: dict[str, Any]) -> dict[str, Any]:
        item = dict(checkpoint)
        thread_id = str(item["thread_id"])
        self._checkpoints.setdefault(thread_id, []).append(item)
        return item

    def list(self, *, thread_id: str, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = [
            dict(x)
            for x in self._checkpoints.get(thread_id, [])
            if x.get("tenant_id") == tenant_id
        ]
        rows.sort(key=lambda x: int(x.get("seq", 0)))
        return rows[: max(1, min(limit, 1000))]


class PostgresWorkflowCheckpointsRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "workflow_checkpoints") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def append(self, *, checkpoint: dict[str, Any]) -> dict[str, Any]:
        item = dict(checkpoint)
        tenant_id = str(item.get("tenant_id") or "tenant_default")
        sql = f"""
            INSERT INTO {self._table_name} (
                checkpoint_id, tenant_id, thread_id, seq, payload
            ) VALUES (%s, %s, %s, %s, %s::jsonb)
            ON CONFLICT(checkpoint_id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                thread_id = EXCLUDED.thread_id,
                seq = EXCLUDED.seq,
                payload = EXCLUDED.payload
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item["checkpoint_id"],
                        tenant_id,
                        item.get("thread_id"),
                        int(item.get("seq", 0)),
                        json.dumps(item, ensure_ascii=True, sort_keys=True),
                    ),
                )
            return item

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def list(self, *, thread_id: str, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE tenant_id = %s AND thread_id = %s
            ORDER BY seq ASC
            LIMIT %s
        """

        def _op(conn: Any) -> list[dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, thread_id, max(1, min(limit, 1000))))
                rows = cur.fetchall() or []
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = row[0]
                if isinstance(payload, dict):
                    out.append(payload)
            return out

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
