from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryParseManifestsRepository:
    def __init__(self, manifests: dict[str, dict[str, Any]]) -> None:
        self._manifests = manifests

    def upsert(self, *, manifest: dict[str, Any]) -> dict[str, Any]:
        item = dict(manifest)
        self._manifests[str(item["job_id"])] = item
        return item

    def get(self, *, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        item = self._manifests.get(job_id)
        if item is None:
            return None
        if item.get("tenant_id") != tenant_id:
            return None
        return item


class PostgresParseManifestsRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "parse_manifests") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def upsert(self, *, tenant_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        payload = dict(manifest)
        payload["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._table_name} (
                job_id, run_id, document_id, tenant_id, selected_parser, parser_version, fallback_chain,
                input_files, started_at, ended_at, status, error_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
            ON CONFLICT(job_id) DO UPDATE
            SET run_id = EXCLUDED.run_id,
                document_id = EXCLUDED.document_id,
                tenant_id = EXCLUDED.tenant_id,
                selected_parser = EXCLUDED.selected_parser,
                parser_version = EXCLUDED.parser_version,
                fallback_chain = EXCLUDED.fallback_chain,
                input_files = EXCLUDED.input_files,
                started_at = EXCLUDED.started_at,
                ended_at = EXCLUDED.ended_at,
                status = EXCLUDED.status,
                error_code = EXCLUDED.error_code
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        payload["job_id"],
                        payload.get("run_id"),
                        payload.get("document_id"),
                        tenant_id,
                        payload.get("selected_parser"),
                        payload.get("parser_version"),
                        json.dumps(payload.get("fallback_chain", []), ensure_ascii=True, sort_keys=True),
                        json.dumps(payload.get("input_files", []), ensure_ascii=True, sort_keys=True),
                        payload.get("started_at"),
                        payload.get("ended_at"),
                        payload.get("status"),
                        payload.get("error_code"),
                    ),
                )
            return payload

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT job_id, run_id, document_id, tenant_id, selected_parser, parser_version,
                   fallback_chain, input_files, started_at, ended_at, status, error_code
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
                "run_id": row[1],
                "document_id": row[2],
                "tenant_id": row[3],
                "selected_parser": row[4],
                "parser_version": row[5],
                "fallback_chain": row[6] if isinstance(row[6], list) else [],
                "input_files": row[7] if isinstance(row[7], list) else [],
                "started_at": row[8],
                "ended_at": row[9],
                "status": row[10],
                "error_code": row[11],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
