#!/usr/bin/env python3
"""Import a real PDF document for testing using internal services.

This script directly calls the internal services using real PostgreSQL and MinIO.

Features:
- Deduplication: Skips import if a document with the same SHA256 hash already exists
- SSOT aligned: Stores to PostgreSQL and MinIO per specification

Usage:
    python scripts/import_real_pdf_direct.py data/your_file.pdf
"""

import hashlib
import os
import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mineru_parse_service import build_mineru_parse_service
from app.object_storage import create_object_storage_from_env
from app.db.postgres import PostgresTxRunner
from app.repositories.documents import PostgresDocumentsRepository
from app.repositories.parse_manifests import PostgresParseManifestsRepository


def compute_file_sha256(file_bytes: bytes) -> str:
    """Compute SHA256 hash of file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def import_pdf(pdf_path: str, tenant_id: str = "test_tenant", force: bool = False):
    """Import and parse a PDF file.

    Args:
        pdf_path: Path to the PDF file
        tenant_id: Tenant ID for multi-tenancy
        force: If True, skip deduplication check and import anyway

    Returns:
        ParseResult on success, None on failure or duplicate
    """
    # Read the PDF file
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    filename = Path(pdf_path).name
    file_sha256 = compute_file_sha256(pdf_bytes)

    # Build services using real PostgreSQL and MinIO
    env = dict(os.environ)

    # Set defaults for local development
    env.setdefault("BEA_OBJECT_STORAGE_BACKEND", "s3")
    env.setdefault("OBJECT_STORAGE_ENDPOINT", "http://localhost:9000")
    env.setdefault("OBJECT_STORAGE_ACCESS_KEY", "minioadmin")
    env.setdefault("OBJECT_STORAGE_SECRET_KEY", "minioadmin")
    env.setdefault("OBJECT_STORAGE_BUCKET", "bea")
    env.setdefault("OBJECT_STORAGE_FORCE_PATH_STYLE", "true")

    # Object storage (MinIO/S3)
    object_storage = create_object_storage_from_env(env)

    # PostgreSQL
    database_url = env.get(
        "DATABASE_URL",
        "postgresql://bea:bea_pass@localhost:5432/bea"
    )
    tx_runner = PostgresTxRunner(database_url)

    # Repositories
    manifests_repo = PostgresParseManifestsRepository(tx_runner=tx_runner)
    documents_repo = PostgresDocumentsRepository(tx_runner=tx_runner)

    # Check for duplicate (unless force=True)
    if not force:
        existing = documents_repo.find_by_file_sha256(
            tenant_id=tenant_id,
            file_sha256=file_sha256,
        )
        if existing:
            print(f"\n⚠️  DUPLICATE DETECTED: Document already exists!")
            print(f"   Document ID: {existing['document_id']}")
            print(f"   Filename: {existing['filename']}")
            print(f"   Status: {existing['status']}")
            print(f"   File SHA256: {file_sha256[:16]}...")
            print(f"\n   Use --force to import anyway, or skip this import.")
            return None

    # Generate deterministic document_id based on file hash (for deduplication)
    document_id = f"doc_{file_sha256[:16]}"
    job_id = f"job_{int(time.time())}"
    run_id = f"run_{int(time.time() * 1000)}"

    print(f"PDF: {pdf_path}")
    print(f"Size: {len(pdf_bytes) / 1024 / 1024:.2f} MB")
    print(f"Document ID: {document_id}")
    print(f"Job ID: {job_id}")
    print(f"Tenant ID: {tenant_id}")
    print("-" * 50)

    # First, upload the file to object storage
    print("Uploading to object storage...")
    storage_uri = object_storage.put_object(
        tenant_id=tenant_id,
        object_type="document",
        object_id=document_id,
        filename=filename,
        content_bytes=pdf_bytes,
        content_type="application/pdf",
    )
    print(f"Storage URI: {storage_uri}")

    # Create document record in PostgreSQL (SSOT §8: raw_file first, then manifest/chunks)
    documents_repo.upsert(
        tenant_id=tenant_id,
        document={
            "document_id": document_id,
            "filename": filename,
            "file_sha256": file_sha256,
            "file_size": len(pdf_bytes),
            "status": "uploaded",
            "storage_uri": storage_uri,
        },
    )
    print("Document record created in PostgreSQL")

    # Build MinerU parse service
    print("Building MinerU parse service...")
    service = build_mineru_parse_service(
        object_storage=object_storage,
        parse_manifests_repo=manifests_repo,
        documents_repo=documents_repo,
        env=env,
    )

    if service is None:
        print("ERROR: MINERU_API_KEY not configured. Cannot parse document.")
        print("Please set MINERU_API_KEY environment variable.")
        return None

    # Parse the document
    print("Starting parse...")
    start_time = time.time()

    try:
        result = service.parse_and_persist_from_bytes(
            file_bytes=pdf_bytes,
            filename=filename,
            document_id=document_id,
            tenant_id=tenant_id,
            job_id=job_id,
        )

        elapsed = time.time() - start_time
        print("-" * 50)
        print(f"Parse completed in {elapsed:.1f}s")
        print(f"Status: {result.status}")
        print(f"Document ID: {result.document_id}")
        print(f"Chunks count: {result.chunks_count}")
        print(f"ZIP storage: {result.zip_storage_uri}")
        if result.full_md:
            print(f"Full MD preview: {result.full_md[:300]}...")

        # Get the chunks from PostgreSQL
        def _query_chunks(conn):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM document_chunks
                    WHERE tenant_id = %s AND document_id = %s
                    """,
                    (tenant_id, document_id)
                )
                count = cur.fetchone()[0]
                print(f"\nTotal chunks in PostgreSQL: {count}")

                if count > 0:
                    cur.execute(
                        """
                        SELECT chunk_type, text, pages
                        FROM document_chunks
                        WHERE tenant_id = %s AND document_id = %s
                        ORDER BY chunk_id
                        LIMIT 1
                        """,
                        (tenant_id, document_id)
                    )
                    row = cur.fetchone()
                    if row:
                        print("\nFirst chunk preview:")
                        print(f"  Type: {row[0]}")
                        print(f"  Text: {row[1][:200] if row[1] else 'N/A'}...")
                        print(f"  Pages: {row[2]}")

        tx_runner.run_in_tx(tenant_id=tenant_id, fn=_query_chunks)

        return result

    except Exception as e:
        print(f"ERROR: Parse failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_real_pdf_direct.py <pdf_path> [--force]")
        print("  --force: Skip deduplication check and import anyway")
        sys.exit(1)

    pdf_path = sys.argv[1]
    force = "--force" in sys.argv

    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    # Check for MINERU_API_KEY
    if not os.environ.get("MINERU_API_KEY"):
        print("WARNING: MINERU_API_KEY not set. Cannot use MinerU cloud parsing.")
        print("Set MINERU_API_KEY for MinerU cloud parsing.")
        sys.exit(1)

    result = import_pdf(pdf_path, force=force)

    if result:
        print("\n" + "=" * 50)
        print("SUCCESS: Document imported and parsed!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("FAILED: Document import failed")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
