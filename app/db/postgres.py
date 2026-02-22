from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _import_psycopg() -> Any:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL backends; install psycopg[binary]") from exc
    return psycopg


class PostgresTxRunner:
    """Run callback logic in one PostgreSQL transaction with tenant session injection."""

    def __init__(self, dsn: str) -> None:
        if not dsn.strip():
            raise ValueError("POSTGRES_DSN must not be empty")
        self._dsn = dsn.strip()

    def run_in_tx(
        self,
        *,
        tenant_id: str,
        fn: Callable[[Any], Any],
    ) -> Any:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be empty")

        psycopg = _import_psycopg()
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.current_tenant', %s, true)", (tenant_id,))
            result = fn(conn)
            conn.commit()
            return result
