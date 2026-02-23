from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryRulePacksRepository:
    def __init__(self, rule_packs: dict[str, dict[str, Any]]) -> None:
        self._rule_packs = rule_packs

    def upsert(self, *, rule_pack: dict[str, Any]) -> dict[str, Any]:
        item = dict(rule_pack)
        self._rule_packs[str(item["rule_pack_version"])] = item
        return item

    def get(self, *, tenant_id: str, rule_pack_version: str) -> dict[str, Any] | None:
        row = self._rule_packs.get(rule_pack_version)
        if row is None or row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [dict(x) for x in self._rule_packs.values() if x.get("tenant_id") == tenant_id]

    def delete(self, *, tenant_id: str, rule_pack_version: str) -> bool:
        row = self._rule_packs.get(rule_pack_version)
        if row is None or row.get("tenant_id") != tenant_id:
            return False
        del self._rule_packs[rule_pack_version]
        return True


class PostgresRulePacksRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "rule_packs") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def upsert(self, *, tenant_id: str, rule_pack: dict[str, Any]) -> dict[str, Any]:
        item = dict(rule_pack)
        item["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._table_name} (
                rule_pack_version, tenant_id, name, status, payload, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT(rule_pack_version) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                name = EXCLUDED.name,
                status = EXCLUDED.status,
                payload = EXCLUDED.payload,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item["rule_pack_version"],
                        tenant_id,
                        item.get("name"),
                        item.get("status"),
                        json.dumps(item, ensure_ascii=True, sort_keys=True),
                        item.get("created_at"),
                        item.get("updated_at"),
                    ),
                )
            return item

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, rule_pack_version: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE tenant_id = %s AND rule_pack_version = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, rule_pack_version))
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
            ORDER BY updated_at DESC
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

    def delete(self, *, tenant_id: str, rule_pack_version: str) -> bool:
        sql = f"DELETE FROM {self._table_name} WHERE tenant_id = %s AND rule_pack_version = %s"

        def _op(conn: Any) -> bool:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, rule_pack_version))
                return cur.rowcount > 0

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
