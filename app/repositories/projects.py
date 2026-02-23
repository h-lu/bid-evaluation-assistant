from __future__ import annotations

import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryProjectsRepository:
    def __init__(self, projects: dict[str, dict[str, Any]]) -> None:
        self._projects = projects

    def upsert(self, *, project: dict[str, Any]) -> dict[str, Any]:
        item = dict(project)
        self._projects[str(item["project_id"])] = item
        return item

    def get(self, *, tenant_id: str, project_id: str) -> dict[str, Any] | None:
        row = self._projects.get(project_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def get_by_code(self, *, tenant_id: str, project_code: str) -> dict[str, Any] | None:
        for row in self._projects.values():
            if row.get("tenant_id") == tenant_id and row.get("project_code") == project_code:
                return dict(row)
        return None

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [dict(x) for x in self._projects.values() if x.get("tenant_id") == tenant_id]

    def delete(self, *, tenant_id: str, project_id: str) -> bool:
        row = self._projects.get(project_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return False
        del self._projects[project_id]
        return True


class PostgresProjectsRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "projects") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def upsert(self, *, tenant_id: str, project: dict[str, Any]) -> dict[str, Any]:
        item = dict(project)
        item["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._table_name} (
                project_id, tenant_id, project_code, name, ruleset_version, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(project_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                project_code = EXCLUDED.project_code,
                name = EXCLUDED.name,
                ruleset_version = EXCLUDED.ruleset_version,
                status = EXCLUDED.status,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item["project_id"],
                        tenant_id,
                        item.get("project_code"),
                        item.get("name"),
                        item.get("ruleset_version"),
                        item.get("status"),
                        item.get("created_at"),
                        item.get("updated_at"),
                    ),
                )
            return item

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, project_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT project_id, tenant_id, project_code, name, ruleset_version, status, created_at, updated_at
            FROM {self._table_name}
            WHERE tenant_id = %s AND project_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, project_id))
                row = cur.fetchone()
            if row is None:
                return None
            return {
                "project_id": row[0],
                "tenant_id": row[1],
                "project_code": row[2],
                "name": row[3],
                "ruleset_version": row[4],
                "status": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get_by_code(self, *, tenant_id: str, project_code: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT project_id, tenant_id, project_code, name, ruleset_version, status, created_at, updated_at
            FROM {self._table_name}
            WHERE tenant_id = %s AND project_code = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, project_code))
                row = cur.fetchone()
            if row is None:
                return None
            return {
                "project_id": row[0],
                "tenant_id": row[1],
                "project_code": row[2],
                "name": row[3],
                "ruleset_version": row[4],
                "status": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def list(self, *, tenant_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT project_id, tenant_id, project_code, name, ruleset_version, status, created_at, updated_at
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
                    "project_id": row[0],
                    "tenant_id": row[1],
                    "project_code": row[2],
                    "name": row[3],
                    "ruleset_version": row[4],
                    "status": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                }
                for row in rows
            ]

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def delete(self, *, tenant_id: str, project_id: str) -> bool:
        sql = f"DELETE FROM {self._table_name} WHERE tenant_id = %s AND project_id = %s"

        def _op(conn: Any) -> bool:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, project_id))
                return cur.rowcount > 0

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
