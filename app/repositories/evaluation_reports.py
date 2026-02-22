from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


class InMemoryEvaluationReportsRepository:
    def __init__(self, reports: dict[str, dict[str, Any]]) -> None:
        self._reports = reports

    def upsert(self, *, report: dict[str, Any]) -> dict[str, Any]:
        item = dict(report)
        self._reports[str(item["evaluation_id"])] = item
        return item

    def get(self, *, tenant_id: str, evaluation_id: str) -> dict[str, Any] | None:
        row = self._reports.get(evaluation_id)
        if row is None:
            return None
        if row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def get_any(self, *, evaluation_id: str) -> dict[str, Any] | None:
        row = self._reports.get(evaluation_id)
        if row is None:
            return None
        return dict(row)


class PostgresEvaluationReportsRepository:
    def __init__(self, *, tx_runner: PostgresTxRunner, table_name: str = "evaluation_reports") -> None:
        self._tx_runner = tx_runner
        self._table_name = _validate_identifier(table_name)

    def upsert(self, *, tenant_id: str, report: dict[str, Any]) -> dict[str, Any]:
        item = dict(report)
        item["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._table_name} (
                evaluation_id, tenant_id, supplier_id, total_score, confidence,
                citation_coverage, risk_level, needs_human_review, trace_id, thread_id,
                interrupt, payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            ON CONFLICT(evaluation_id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                supplier_id = EXCLUDED.supplier_id,
                total_score = EXCLUDED.total_score,
                confidence = EXCLUDED.confidence,
                citation_coverage = EXCLUDED.citation_coverage,
                risk_level = EXCLUDED.risk_level,
                needs_human_review = EXCLUDED.needs_human_review,
                trace_id = EXCLUDED.trace_id,
                thread_id = EXCLUDED.thread_id,
                interrupt = EXCLUDED.interrupt,
                payload = EXCLUDED.payload
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item["evaluation_id"],
                        tenant_id,
                        item.get("supplier_id"),
                        float(item.get("total_score", 0.0)),
                        float(item.get("confidence", 0.0)),
                        float(item.get("citation_coverage", 0.0)),
                        item.get("risk_level"),
                        bool(item.get("needs_human_review", False)),
                        item.get("trace_id"),
                        item.get("thread_id"),
                        json.dumps(item.get("interrupt"), ensure_ascii=True, sort_keys=True),
                        json.dumps(item, ensure_ascii=True, sort_keys=True),
                    ),
                )
            return item

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, evaluation_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE tenant_id = %s AND evaluation_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, evaluation_id))
                row = cur.fetchone()
            if row is None:
                return None
            payload = row[0]
            return payload if isinstance(payload, dict) else None

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get_any(self, *, evaluation_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT payload
            FROM {self._table_name}
            WHERE evaluation_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (evaluation_id,))
                row = cur.fetchone()
            if row is None:
                return None
            payload = row[0]
            return payload if isinstance(payload, dict) else None

        return self._tx_runner.run_in_tx(tenant_id="tenant_default", fn=_op)
