from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemorySuppliersRepository:
    def __init__(self, suppliers: dict[str, dict[str, Any]]) -> None:
        self._suppliers = suppliers

    def upsert(self, *, supplier: dict[str, Any]) -> dict[str, Any]:
        item = dict(supplier)
        self._suppliers[str(item["supplier_id"])] = item
        return item

    def get(self, *, tenant_id: str, supplier_id: str) -> dict[str, Any] | None:
        row = self._suppliers.get(supplier_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def get_by_code(self, *, tenant_id: str, supplier_code: str) -> dict[str, Any] | None:
        for row in self._suppliers.values():
            if row.get("tenant_id") == tenant_id and row.get("supplier_code") == supplier_code:
                return dict(row)
        return None

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [dict(x) for x in self._suppliers.values() if x.get("tenant_id") == tenant_id]

    def delete(self, *, tenant_id: str, supplier_id: str) -> bool:
        row = self._suppliers.get(supplier_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return False
        del self._suppliers[supplier_id]
        return True


class PostgresSuppliersRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "suppliers") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def upsert(self, *, tenant_id: str, supplier: dict[str, Any]) -> dict[str, Any]:
        item = dict(supplier)
        item["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._table_name} (
                supplier_id, tenant_id, supplier_code, name, qualification_json, risk_flags_json, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
            ON CONFLICT(supplier_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                supplier_code = EXCLUDED.supplier_code,
                name = EXCLUDED.name,
                qualification_json = EXCLUDED.qualification_json,
                risk_flags_json = EXCLUDED.risk_flags_json,
                status = EXCLUDED.status,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item["supplier_id"],
                        tenant_id,
                        item.get("supplier_code"),
                        item.get("name"),
                        json.dumps(item.get("qualification", {}), ensure_ascii=True, sort_keys=True),
                        json.dumps(item.get("risk_flags", {}), ensure_ascii=True, sort_keys=True),
                        item.get("status"),
                        item.get("created_at"),
                        item.get("updated_at"),
                    ),
                )
            return item

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, supplier_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT supplier_id, tenant_id, supplier_code, name, qualification_json, risk_flags_json, status, created_at, updated_at
            FROM {self._table_name}
            WHERE tenant_id = %s AND supplier_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, supplier_id))
                row = cur.fetchone()
            if row is None:
                return None
            return {
                "supplier_id": row[0],
                "tenant_id": row[1],
                "supplier_code": row[2],
                "name": row[3],
                "qualification": row[4] if isinstance(row[4], dict) else {},
                "risk_flags": row[5] if isinstance(row[5], dict) else {},
                "status": row[6],
                "created_at": row[7],
                "updated_at": row[8],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get_by_code(self, *, tenant_id: str, supplier_code: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT supplier_id, tenant_id, supplier_code, name, qualification_json, risk_flags_json, status, created_at, updated_at
            FROM {self._table_name}
            WHERE tenant_id = %s AND supplier_code = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, supplier_code))
                row = cur.fetchone()
            if row is None:
                return None
            return {
                "supplier_id": row[0],
                "tenant_id": row[1],
                "supplier_code": row[2],
                "name": row[3],
                "qualification": row[4] if isinstance(row[4], dict) else {},
                "risk_flags": row[5] if isinstance(row[5], dict) else {},
                "status": row[6],
                "created_at": row[7],
                "updated_at": row[8],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT supplier_id, tenant_id, supplier_code, name, qualification_json, risk_flags_json, status, created_at, updated_at
            FROM {self._table_name}
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """

        def _op(conn: Any) -> list[dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id,))
                rows = cur.fetchall() or []
            return [
                {
                    "supplier_id": row[0],
                    "tenant_id": row[1],
                    "supplier_code": row[2],
                    "name": row[3],
                    "qualification": row[4] if isinstance(row[4], dict) else {},
                    "risk_flags": row[5] if isinstance(row[5], dict) else {},
                    "status": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                }
                for row in rows
            ]

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def delete(self, *, tenant_id: str, supplier_id: str) -> bool:
        sql = f"DELETE FROM {self._table_name} WHERE tenant_id = %s AND supplier_id = %s"

        def _op(conn: Any) -> bool:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, supplier_id))
                return cur.rowcount > 0

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
