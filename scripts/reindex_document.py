#!/usr/bin/env python3
"""
Re-index existing document chunks to LightRAG.

Usage:
    python scripts/reindex_document.py --document-id <doc_id> [--tenant-id <tenant_id>]
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError


def get_chunks_from_db(tenant_id: str, document_id: str) -> list[dict]:
    """Fetch chunks from PostgreSQL database."""
    import psycopg

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://bea:bea_pass@localhost:5432/bea"
    )

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_id, document_id, tenant_id,
                       chunk_hash, pages, positions, section, heading_path,
                       chunk_type, parser, parser_version, text
                FROM document_chunks
                WHERE tenant_id = %s AND document_id = %s
                """,
                (tenant_id, document_id)
            )
            rows = cur.fetchall()

    chunks = []
    for row in rows:
        chunks.append({
            "chunk_id": row[0],
            "document_id": row[1],
            "tenant_id": row[2],
            "chunk_hash": row[3],
            "pages": row[4],
            "positions": row[5],
            "section": row[6],
            "heading_path": row[7],
            "chunk_type": row[8],
            "parser": row[9],
            "parser_version": row[10],
            "text": row[11],
        })
    return chunks


def index_to_lightrag(
    index_name: str,
    tenant_id: str,
    project_id: str,
    supplier_id: str,
    document_id: str,
    doc_type: str,
    chunks: list[dict],
) -> int:
    """Send chunks to LightRAG /index endpoint."""
    lightrag_dsn = os.environ.get("LIGHTRAG_DSN", "http://localhost:8081")
    endpoint = f"{lightrag_dsn.rstrip('/')}/index"

    payload = {
        "index_name": index_name,
        "tenant_id": tenant_id,
        "project_id": project_id or "",
        "supplier_id": supplier_id or "",
        "document_id": document_id,
        "doc_type": doc_type or "",
        "chunks": chunks,
    }

    req = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("indexed", 0)
    except URLError as e:
        print(f"Error indexing to LightRAG: {e}")
        return 0


def update_document_status(document_id: str, status: str) -> bool:
    """Update document status in database."""
    import psycopg

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://bea:bea_pass@localhost:5432/bea"
    )

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET status = %s WHERE document_id = %s",
                    (status, document_id)
                )
                conn.commit()
        return True
    except Exception as e:
        print(f"Error updating document status: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Re-index document chunks to LightRAG")
    parser.add_argument("--document-id", required=True, help="Document ID to re-index")
    parser.add_argument("--tenant-id", default="test_tenant", help="Tenant ID")
    parser.add_argument("--project-id", default="", help="Project ID")
    parser.add_argument("--supplier-id", default="", help="Supplier ID")
    parser.add_argument("--doc-type", default="", help="Document type")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be indexed")
    args = parser.parse_args()

    print(f"Fetching chunks for document: {args.document_id}")
    chunks = get_chunks_from_db(args.tenant_id, args.document_id)
    print(f"Found {len(chunks)} chunks")

    if args.dry_run:
        print("Dry run - would index the following chunks:")
        for chunk in chunks[:3]:
            print(f"  - {chunk['chunk_id']}: {chunk.get('text', '')[:50]}...")
        print(f"  ... and {len(chunks) - 3} more")
        return

    index_name = f"{args.tenant_id}_{args.project_id or 'default'}"
    print(f"Indexing to collection: {index_name}")

    indexed = index_to_lightrag(
        index_name=index_name,
        tenant_id=args.tenant_id,
        project_id=args.project_id,
        supplier_id=args.supplier_id,
        document_id=args.document_id,
        doc_type=args.doc_type,
        chunks=chunks,
    )
    print(f"Indexed {indexed} chunks to LightRAG")

    if indexed > 0:
        print("Updating document status to 'indexed'")
        if update_document_status(args.document_id, "indexed"):
            print("Document status updated successfully")
        else:
            print("Failed to update document status")


if __name__ == "__main__":
    main()
