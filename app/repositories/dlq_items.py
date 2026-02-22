from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryDlqItemsRepository:
    def __init__(self, items: dict[str, dict[str, Any]]) -> None:
        self._items = items

    def upsert(self, *, item: dict[str, Any]) -> dict[str, Any]:
        row = dict(item)
        self._items[str(row["dlq_id"])] = row
        return row

    def get(self, *, tenant_id: str, dlq_id: str) -> dict[str, Any] | None:
        row = self._items.get(dlq_id)
        if row is None:
            return None
        if row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        rows = [dict(x) for x in self._items.values() if x.get("tenant_id") == tenant_id]
        rows.sort(key=lambda x: str(x.get("dlq_id", "")))
        return rows


class PostgresDlqItemsRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "dlq_items") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def upsert(self, *, item: dict[str, Any]) -> dict[str, Any]:
        row = dict(item)
        tenant_id = str(row.get("tenant_id") or "tenant_default")
        status = str(row.get("status") or "open")
        sql = f"""
            INSERT INTO {self._table_name} (
                dlq_id, tenant_id, status, payload
            ) VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT(dlq_id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                status = EXCLUDED.status,
                payload = EXCLUDED.payload
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        row["dlq_id"],
                        tenant_id,
                        status,
                        json.dumps(row, ensure_ascii=True, sort_keys=True),
                    ),
                )
            return row

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, dlq_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE tenant_id = %s AND dlq_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, dlq_id))
                row = cur.fetchone()
            if row is None:
                return None
            payload = row[0]
            return payload if isinstance(payload, dict) else None

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE tenant_id = %s
            ORDER BY dlq_id ASC
        """

        def _op(conn: Any) -> list[dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id,))
                rows = cur.fetchall() or []
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = row[0]
                if isinstance(payload, dict):
                    out.append(payload)
            return out

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
