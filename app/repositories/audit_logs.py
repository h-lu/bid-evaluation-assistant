from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryAuditLogsRepository:
    def __init__(self, audit_logs: list[dict[str, Any]]) -> None:
        self._audit_logs = audit_logs

    def append(self, *, log: dict[str, Any]) -> dict[str, Any]:
        item = dict(log)
        self._audit_logs.append(item)
        return item

    def list_for_evaluation(self, *, tenant_id: str, evaluation_id: str) -> list[dict[str, Any]]:
        return [
            dict(x)
            for x in self._audit_logs
            if x.get("tenant_id") == tenant_id and x.get("evaluation_id") == evaluation_id
        ]


class PostgresAuditLogsRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "audit_logs") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def append(self, *, log: dict[str, Any]) -> dict[str, Any]:
        item = dict(log)
        tenant_id = str(item.get("tenant_id") or "tenant_default")
        sql = f"""
            INSERT INTO {self._table_name} (
                audit_id, tenant_id, evaluation_id, action, occurred_at, payload
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT(audit_id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                evaluation_id = EXCLUDED.evaluation_id,
                action = EXCLUDED.action,
                occurred_at = EXCLUDED.occurred_at,
                payload = EXCLUDED.payload
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item["audit_id"],
                        tenant_id,
                        item.get("evaluation_id"),
                        item.get("action"),
                        item.get("occurred_at"),
                        json.dumps(item, ensure_ascii=True, sort_keys=True),
                    ),
                )
            return item

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def list_for_evaluation(self, *, tenant_id: str, evaluation_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE tenant_id = %s AND evaluation_id = %s
            ORDER BY occurred_at ASC
        """

        def _op(conn: Any) -> list[dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, evaluation_id))
                rows = cur.fetchall() or []
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = row[0]
                if isinstance(payload, dict):
                    out.append(payload)
            return out

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
