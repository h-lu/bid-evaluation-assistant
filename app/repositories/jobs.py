from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryJobsRepository:
    def __init__(self, jobs: dict[str, dict[str, Any]]) -> None:
        self._jobs = jobs

    def create(self, *, job: dict[str, Any]) -> dict[str, Any]:
        self._jobs[str(job["job_id"])] = dict(job)
        return dict(job)

    def get(self, *, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        row = self._jobs.get(job_id)
        if row is None:
            return None
        if row.get("tenant_id") != tenant_id:
            return None
        return dict(row)


class PostgresJobsRepository:
    """Jobs repository for postgres backend; keeps tenant_id in every query scope."""

    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "jobs") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def create(self, *, tenant_id: str, job: dict[str, Any]) -> dict[str, Any]:
        payload = dict(job)
        payload["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._table_name} (
                job_id, tenant_id, job_type, status, retry_count, thread_id, trace_id, resource, payload, last_error
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        payload["job_id"],
                        tenant_id,
                        payload.get("job_type", ""),
                        payload.get("status", "queued"),
                        int(payload.get("retry_count", 0)),
                        payload.get("thread_id", ""),
                        payload.get("trace_id", ""),
                        json.dumps(payload.get("resource", {}), ensure_ascii=True, sort_keys=True),
                        json.dumps(payload.get("payload", {}), ensure_ascii=True, sort_keys=True),
                        json.dumps(payload.get("last_error"), ensure_ascii=True, sort_keys=True),
                    ),
                )
            return payload

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT job_id, tenant_id, job_type, status, retry_count, thread_id, trace_id, resource, payload, last_error
            FROM {self._table_name}
            WHERE tenant_id = %s AND job_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, job_id))
                row = cur.fetchone()
            if row is None:
                return None
            return {
                "job_id": row[0],
                "tenant_id": row[1],
                "job_type": row[2],
                "status": row[3],
                "retry_count": int(row[4]),
                "thread_id": row[5],
                "trace_id": row[6],
                "resource": row[7] if isinstance(row[7], dict) else {},
                "payload": row[8] if isinstance(row[8], dict) else {},
                "last_error": row[9],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
