from __future__ import annotations

import re
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


class PostgresRlsManager:
    """Apply RLS tenant policies on PostgreSQL tables."""

    DEFAULT_TABLES: tuple[str, ...] = (
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
    )

    def __init__(self, dsn: str, *, tables: list[str] | tuple[str, ...] | None = None) -> None:
        if not dsn.strip():
            raise ValueError("POSTGRES_DSN must not be empty")
        self._dsn = dsn.strip()
        target_tables = list(self.DEFAULT_TABLES if tables is None else tables)
        if not target_tables:
            raise ValueError("tables must not be empty")
        self._tables = [_validate_identifier(name) for name in target_tables]

    def apply(self) -> list[str]:
        psycopg = _import_psycopg()
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                for table in self._tables:
                    policy = f"{table}_tenant_isolation"
                    cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                    cur.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
                    cur.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
                    cur.execute(
                        f"""
                        CREATE POLICY {policy} ON {table}
                        USING ({table}.tenant_id = current_setting('app.current_tenant', true))
                        WITH CHECK ({table}.tenant_id = current_setting('app.current_tenant', true))
                        """
                    )
            conn.commit()
        return list(self._tables)
