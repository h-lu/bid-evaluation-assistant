from __future__ import annotations

import json
import re
from typing import Any

from app.db.postgres import PostgresTxRunner


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"invalid SQL identifier: {name}")
    return name


def _with_page_bbox(chunk: dict[str, Any]) -> dict[str, Any]:
    item = dict(chunk)
    positions = item.get("positions")
    if isinstance(positions, list) and positions and isinstance(positions[0], dict):
        item.setdefault("page", int(positions[0].get("page") or 1))
        bbox = positions[0].get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            item.setdefault("bbox", bbox)
    item.setdefault("page", int(item.get("page") or 1))
    item.setdefault("bbox", [0, 0, 1, 1])
    return item


class InMemoryDocumentsRepository:
    def __init__(
        self,
        documents: dict[str, dict[str, Any]],
        document_chunks: dict[str, list[dict[str, Any]]],
    ) -> None:
        self._documents = documents
        self._document_chunks = document_chunks

    def upsert(self, *, document: dict[str, Any]) -> dict[str, Any]:
        doc = dict(document)
        document_id = str(doc["document_id"])
        self._documents[document_id] = doc
        self._document_chunks.setdefault(document_id, [])
        return doc

    def get(self, *, tenant_id: str, document_id: str) -> dict[str, Any] | None:
        row = self._documents.get(document_id)
        if row is None:
            return None
        if row.get("tenant_id") != tenant_id:
            return None
        return dict(row)

    def replace_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        row = self._documents.get(document_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return []
        copied = [dict(x) for x in chunks]
        self._document_chunks[document_id] = copied
        return copied

    def list_chunks(self, *, tenant_id: str, document_id: str) -> list[dict[str, Any]]:
        row = self._documents.get(document_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return []
        return [_with_page_bbox(dict(x)) for x in self._document_chunks.get(document_id, [])]


class PostgresDocumentsRepository:
    def __init__(
        self,
        *,
        tx_runner: PostgresTxRunner,
        documents_table: str = "documents",
        chunks_table: str = "document_chunks",
    ) -> None:
        self._tx_runner = tx_runner
        self._documents_table = _validate_identifier(documents_table)
        self._chunks_table = _validate_identifier(chunks_table)

    def upsert(self, *, tenant_id: str, document: dict[str, Any]) -> dict[str, Any]:
        payload = dict(document)
        payload["tenant_id"] = tenant_id
        sql = f"""
            INSERT INTO {self._documents_table} (
                document_id, tenant_id, project_id, supplier_id, doc_type, filename, file_sha256, file_size, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(document_id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                project_id = EXCLUDED.project_id,
                supplier_id = EXCLUDED.supplier_id,
                doc_type = EXCLUDED.doc_type,
                filename = EXCLUDED.filename,
                file_sha256 = EXCLUDED.file_sha256,
                file_size = EXCLUDED.file_size,
                status = EXCLUDED.status
        """

        def _op(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        payload["document_id"],
                        tenant_id,
                        payload.get("project_id"),
                        payload.get("supplier_id"),
                        payload.get("doc_type"),
                        payload.get("filename"),
                        payload.get("file_sha256"),
                        int(payload.get("file_size") or 0),
                        payload.get("status", "uploaded"),
                    ),
                )
            return payload

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def get(self, *, tenant_id: str, document_id: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT document_id, tenant_id, project_id, supplier_id, doc_type, filename, file_sha256, file_size, status
            FROM {self._documents_table}
            WHERE tenant_id = %s AND document_id = %s
            LIMIT 1
        """

        def _op(conn: Any) -> dict[str, Any] | None:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, document_id))
                row = cur.fetchone()
            if row is None:
                return None
            return {
                "document_id": row[0],
                "tenant_id": row[1],
                "project_id": row[2],
                "supplier_id": row[3],
                "doc_type": row[4],
                "filename": row[5],
                "file_sha256": row[6],
                "file_size": int(row[7] or 0),
                "status": row[8],
            }

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def replace_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        delete_sql = f"DELETE FROM {self._chunks_table} WHERE tenant_id = %s AND document_id = %s"
        insert_sql = f"""
            INSERT INTO {self._chunks_table} (
                chunk_id, tenant_id, document_id, chunk_hash, pages, positions, section, heading_path, chunk_type, parser, parser_version, text
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s, %s)
        """

        copied = [dict(x) for x in chunks]

        def _op(conn: Any) -> list[dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(delete_sql, (tenant_id, document_id))
                for chunk in copied:
                    cur.execute(
                        insert_sql,
                        (
                            chunk.get("chunk_id"),
                            tenant_id,
                            document_id,
                            chunk.get("chunk_hash", ""),
                            json.dumps(chunk.get("pages", []), ensure_ascii=True, sort_keys=True),
                            json.dumps(chunk.get("positions", []), ensure_ascii=True, sort_keys=True),
                            chunk.get("section", ""),
                            json.dumps(chunk.get("heading_path", []), ensure_ascii=True, sort_keys=True),
                            chunk.get("chunk_type", "text"),
                            chunk.get("parser", "mineru"),
                            chunk.get("parser_version", "v0"),
                            chunk.get("text", ""),
                        ),
                    )
            return copied

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)

    def list_chunks(self, *, tenant_id: str, document_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT chunk_id, document_id, chunk_hash, pages, positions, section, heading_path, chunk_type, parser, parser_version, text
            FROM {self._chunks_table}
            WHERE tenant_id = %s AND document_id = %s
            ORDER BY chunk_id ASC
        """

        def _op(conn: Any) -> list[dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(sql, (tenant_id, document_id))
                rows = cur.fetchall() or []
            items: list[dict[str, Any]] = []
            for row in rows:
                items.append(
                    _with_page_bbox(
                        {
                            "chunk_id": row[0],
                            "document_id": row[1],
                            "chunk_hash": row[2],
                            "pages": row[3] if isinstance(row[3], list) else [],
                            "positions": row[4] if isinstance(row[4], list) else [],
                            "section": row[5],
                            "heading_path": row[6] if isinstance(row[6], list) else [],
                            "chunk_type": row[7],
                            "parser": row[8],
                            "parser_version": row[9],
                            "text": row[10],
                        }
                    )
                )
            return items

        return self._tx_runner.run_in_tx(tenant_id=tenant_id, fn=_op)
