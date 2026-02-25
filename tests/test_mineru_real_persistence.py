"""Real MinerU API persistence tests with MinIO and PostgreSQL.

These tests use:
- Real MinerU Official API (requires MINERU_API_KEY)
- Real MinIO/S3 storage (requires running Docker containers)
- Real PostgreSQL database (requires running Docker containers)

Prerequisites:
1. Docker containers running: docker-compose -f docker-compose.production.yml up -d
2. MINERU_API_KEY environment variable set

Run with: pytest tests/test_mineru_real_persistence.py -v -m real_mineru

To skip these tests (default): pytest -v -m "not real_mineru"
"""
from __future__ import annotations

import io
import os
import zipfile
from datetime import UTC, datetime
from typing import Any

import pytest

# Skip all tests in this module if MINERU_API_KEY not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("MINERU_API_KEY", "").strip(),
    reason="MINERU_API_KEY not set - run with -m real_mineru to include",
)


# ============================================================================
# Real Backend Fixtures
# ============================================================================

@pytest.fixture
def real_s3_storage():
    """Create real S3ObjectStorage connected to MinIO.

    Requires MinIO container running:
    docker-compose -f docker-compose.production.yml up -d minio
    """
    from app.object_storage import S3ObjectStorage, ObjectStorageConfig

    config = ObjectStorageConfig(
        backend="s3",
        bucket="bea",
        root="/tmp",  # Not used for S3
        prefix="",
        worm_mode=False,
        endpoint="http://localhost:9000",
        public_endpoint="http://localhost:9000",
        region="us-east-1",
        access_key="minioadmin",
        secret_key="minioadmin",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    return S3ObjectStorage(config=config)


@pytest.fixture
def real_postgres_connection():
    """Create real PostgreSQL connection.

    Requires PostgreSQL container running:
    docker-compose -f docker-compose.production.yml up -d postgres
    """
    import psycopg
    from psycopg.rows import dict_row

    dsn = "postgresql://bea:bea_pass@localhost:5432/bea"
    conn = psycopg.connect(dsn, row_factory=dict_row)
    yield conn
    conn.close()


class RealParseManifestsRepo:
    """Real parse manifests repository using PostgreSQL."""

    def __init__(self, conn):
        self._conn = conn

    def _set_tenant(self, cur, tenant_id: str):
        """Set tenant context for RLS using safe string formatting."""
        from psycopg import sql
        cur.execute(sql.SQL("SET app.current_tenant = {}").format(sql.Literal(tenant_id)))

    def upsert(self, *, tenant_id: str, manifest: dict) -> dict:
        import json
        with self._conn.cursor() as cur:
            self._set_tenant(cur, tenant_id)
            cur.execute("""
                INSERT INTO parse_manifests (job_id, run_id, document_id, tenant_id, selected_parser,
                    parser_version, fallback_chain, input_files, started_at, ended_at, status, error_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    document_id = EXCLUDED.document_id,
                    selected_parser = EXCLUDED.selected_parser,
                    parser_version = EXCLUDED.parser_version,
                    fallback_chain = EXCLUDED.fallback_chain,
                    input_files = EXCLUDED.input_files,
                    started_at = EXCLUDED.started_at,
                    ended_at = EXCLUDED.ended_at,
                    status = EXCLUDED.status,
                    error_code = EXCLUDED.error_code
            """, (
                manifest.get("job_id"),
                manifest.get("run_id", manifest.get("job_id")),
                manifest.get("document_id"),
                tenant_id,
                manifest.get("selected_parser"),
                manifest.get("parser_version"),
                json.dumps(manifest.get("fallback_chain", [])),
                json.dumps(manifest.get("input_files", [])),
                manifest.get("started_at"),
                manifest.get("ended_at"),
                manifest.get("status"),
                manifest.get("error_code"),
            ))
            self._conn.commit()
        return manifest

    def get(self, *, tenant_id: str, job_id: str) -> dict | None:
        with self._conn.cursor() as cur:
            self._set_tenant(cur, tenant_id)
            cur.execute("""
                SELECT * FROM parse_manifests
                WHERE job_id = %s
            """, (job_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None


class RealDocumentsRepo:
    """Real documents repository using PostgreSQL."""

    def __init__(self, conn):
        self._conn = conn

    def _set_tenant(self, cur, tenant_id: str):
        """Set tenant context for RLS using safe string formatting."""
        from psycopg import sql
        cur.execute(sql.SQL("SET app.current_tenant = {}").format(sql.Literal(tenant_id)))

    def upsert_document(self, *, document: dict) -> dict:
        with self._conn.cursor() as cur:
            tenant_id = document.get("tenant_id")
            self._set_tenant(cur, tenant_id)
            cur.execute("""
                INSERT INTO documents (document_id, tenant_id, project_id, supplier_id,
                    doc_type, filename, file_sha256, file_size, status, storage_uri)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    storage_uri = EXCLUDED.storage_uri
            """, (
                document.get("document_id"),
                tenant_id,
                document.get("project_id"),
                document.get("supplier_id"),
                document.get("doc_type"),
                document.get("filename"),
                document.get("file_sha256"),
                document.get("file_size"),
                document.get("status"),
                document.get("storage_uri"),
            ))
            self._conn.commit()
        return document

    def get(self, *, tenant_id: str, document_id: str) -> dict | None:
        with self._conn.cursor() as cur:
            self._set_tenant(cur, tenant_id)
            cur.execute("""
                SELECT * FROM documents
                WHERE document_id = %s
            """, (document_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    def replace_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict],
    ) -> list[dict]:
        import json
        with self._conn.cursor() as cur:
            self._set_tenant(cur, tenant_id)

            # Delete existing chunks
            cur.execute("""
                DELETE FROM document_chunks
                WHERE document_id = %s
            """, (document_id,))

            # Insert new chunks
            for chunk in chunks:
                cur.execute("""
                    INSERT INTO document_chunks (
                        chunk_id, tenant_id, document_id, chunk_hash,
                        pages, positions, section, heading_path, chunk_type,
                        parser, parser_version, text
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s, %s)
                """, (
                    chunk.get("chunk_id"),
                    tenant_id,
                    document_id,
                    chunk.get("chunk_hash"),
                    json.dumps(chunk.get("pages", [])),
                    json.dumps(chunk.get("positions", [])),
                    chunk.get("section"),
                    json.dumps(chunk.get("heading_path", [])),
                    chunk.get("chunk_type"),
                    chunk.get("parser"),
                    chunk.get("parser_version"),
                    chunk.get("text"),
                ))
            self._conn.commit()
        return chunks

    def get_chunks(self, *, tenant_id: str, document_id: str) -> list[dict]:
        with self._conn.cursor() as cur:
            self._set_tenant(cur, tenant_id)
            cur.execute("""
                SELECT * FROM document_chunks
                WHERE document_id = %s
                ORDER BY pages::text, positions::text
            """, (document_id,))
            return [dict(row) for row in cur.fetchall()]


@pytest.fixture
def real_manifests_repo(real_postgres_connection):
    return RealParseManifestsRepo(real_postgres_connection)


@pytest.fixture
def real_documents_repo(real_postgres_connection):
    return RealDocumentsRepo(real_postgres_connection)


@pytest.fixture
def real_service(real_s3_storage, real_manifests_repo, real_documents_repo):
    """Create service with real MinIO and PostgreSQL backends."""
    from app.mineru_parse_service import build_mineru_parse_service

    service = build_mineru_parse_service(
        object_storage=real_s3_storage,
        parse_manifests_repo=real_manifests_repo,
        documents_repo=real_documents_repo,
    )
    assert service is not None, "MINERU_API_KEY required for real tests"
    return service


@pytest.fixture
def sample_pdf_bytes():
    """Create a sample PDF for testing."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test Document for MinerU Real Integration", fontsize=16)
    page.insert_text((72, 100), "This is a test PDF file created for integration testing.", fontsize=11)
    page.insert_text((72, 120), "Content includes: technical specifications, pricing, and compliance.", fontsize=11)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ============================================================================
# Test Classes
# ============================================================================

@pytest.mark.real_mineru
@pytest.mark.slow
class TestRealMineruWithMinioAndPostgres:
    """Real persistence tests with MinerU API, MinIO, and PostgreSQL."""

    def test_full_parse_and_persist_with_url(
        self,
        real_service,
        real_s3_storage,
        real_manifests_repo,
        real_documents_repo,
        real_postgres_connection,
    ):
        """Test complete parse flow with URL-based API.

        Flow:
        1. Call MinerU API with URL
        2. Download result zip
        3. Save zip to MinIO
        4. Extract and save images to MinIO
        5. Parse content_list to chunks
        6. Persist chunks to PostgreSQL
        """
        import time

        doc_id = f"doc_url_{int(time.time())}"
        job_id = f"job_url_{int(time.time())}"

        result = real_service.parse_and_persist(
            file_url="https://arxiv.org/pdf/2305.12002.pdf",
            document_id=doc_id,
            tenant_id="tenant_real_test",
            job_id=job_id,
        )

        # Verify result
        assert result.status == "completed"
        assert result.document_id == doc_id
        assert result.chunks_count > 0
        assert result.zip_storage_uri is not None
        assert result.full_md is not None

        # Verify zip saved to MinIO
        zip_bytes = real_s3_storage.get_object(storage_uri=result.zip_storage_uri)
        assert len(zip_bytes) > 0
        assert zip_bytes[:4] == b"PK\x03\x04"  # ZIP magic bytes

        print(f"\n=== URL-based Parse Result ===")
        print(f"Status: {result.status}")
        print(f"Chunks: {result.chunks_count}")
        print(f"Parse time: {result.parse_time_s:.2f}s")
        print(f"Zip URI: {result.zip_storage_uri}")
        print(f"Zip size: {len(zip_bytes)} bytes")
        print(f"Images: {result.images_count}")

        # Verify manifest in PostgreSQL
        manifest = real_manifests_repo.get(tenant_id="tenant_real_test", job_id=job_id)
        assert manifest is not None
        assert manifest["status"] == "completed"
        assert manifest["error_code"] is None

        # Verify chunks in PostgreSQL
        chunks = real_documents_repo.get_chunks(
            tenant_id="tenant_real_test",
            document_id=doc_id,
        )
        assert len(chunks) > 0

        # Verify chunk fields per SSOT §7.3
        first_chunk = chunks[0]
        required_fields = [
            "chunk_id",
            "tenant_id",
            "document_id",
            "pages",
            "positions",
            "section",
            "heading_path",
            "chunk_type",
            "parser",
            "parser_version",
            "text",
        ]
        for field in required_fields:
            assert field in first_chunk, f"Missing required field: {field}"

        print(f"\n=== PostgreSQL Chunks ===")
        print(f"Total chunks: {len(chunks)}")
        print(f"First chunk ID: {first_chunk.get('chunk_id')}")
        print(f"First chunk text preview: {first_chunk.get('text', '')[:100]}...")

    @pytest.mark.slow
    def test_full_parse_and_persist_with_file_upload(
        self,
        real_s3_storage,
        real_manifests_repo,
        real_documents_repo,
        sample_pdf_bytes,
    ):
        """Test complete parse flow with File Upload API.

        Flow:
        1. Request upload URL from MinerU
        2. Upload file bytes to cloud storage
        3. Poll for completion
        4. Save result zip to MinIO
        5. Parse content_list to chunks
        6. Persist chunks to PostgreSQL

        Note: This test is marked as 'slow' because MinerU cloud processing
        can take several minutes. Run with: pytest -m 'not slow' to skip.
        """
        import time

        from app.mineru_parse_service import build_mineru_parse_service

        # Create service with longer timeout for file upload (MinerU cloud is slower)
        service = build_mineru_parse_service(
            object_storage=real_s3_storage,
            parse_manifests_repo=real_manifests_repo,
            documents_repo=real_documents_repo,
            env={
                **os.environ,
                "MINERU_MAX_POLL_TIME_S": "600",  # 10 minutes for file upload
            },
        )
        assert service is not None, "MINERU_API_KEY required for real tests"

        doc_id = f"doc_upload_{int(time.time())}"
        job_id = f"job_upload_{int(time.time())}"

        # First, save the sample PDF to MinIO
        storage_uri = real_s3_storage.put_object(
            tenant_id="tenant_real_test",
            object_type="document",
            object_id=doc_id,
            filename="test_document.pdf",
            content_bytes=sample_pdf_bytes,
            content_type="application/pdf",
        )

        print(f"\n=== File Upload Test ===")
        print(f"Saved PDF to: {storage_uri}")
        print(f"PDF size: {len(sample_pdf_bytes)} bytes")

        # Use file upload API
        result = service.parse_and_persist_from_bytes(
            file_bytes=sample_pdf_bytes,
            filename="test_document.pdf",
            document_id=doc_id,
            tenant_id="tenant_real_test",
            job_id=job_id,
        )

        # Verify result
        assert result.status == "completed"
        assert result.document_id == doc_id
        assert result.chunks_count >= 0  # May be 0 for simple PDF
        assert result.zip_storage_uri is not None

        print(f"\n=== File Upload Parse Result ===")
        print(f"Status: {result.status}")
        print(f"Chunks: {result.chunks_count}")
        print(f"Parse time: {result.parse_time_s:.2f}s")
        print(f"Zip URI: {result.zip_storage_uri}")

        # Verify zip saved to MinIO
        zip_bytes = real_s3_storage.get_object(storage_uri=result.zip_storage_uri)
        assert len(zip_bytes) > 0
        assert zip_bytes[:4] == b"PK\x03\x04"

        # Verify manifest in PostgreSQL
        manifest = real_manifests_repo.get(tenant_id="tenant_real_test", job_id=job_id)
        assert manifest is not None
        assert manifest["status"] == "completed"

    def test_verify_minio_storage_structure(
        self,
        real_service,
        real_s3_storage,
    ):
        """Verify MinIO storage follows SSOT structure."""
        import time

        doc_id = f"doc_structure_{int(time.time())}"
        job_id = f"job_structure_{int(time.time())}"

        result = real_service.parse_and_persist(
            file_url="https://arxiv.org/pdf/2305.12002.pdf",
            document_id=doc_id,
            tenant_id="tenant_real_test",
            job_id=job_id,
        )

        # Verify storage URI format
        # Expected: object://s3/bea/tenants/{tenant_id}/document_parse/{doc_id}/result.zip
        assert result.zip_storage_uri.startswith("object://s3/bea/tenants/")
        assert "document_parse" in result.zip_storage_uri
        assert doc_id in result.zip_storage_uri

        # Download and inspect zip structure
        zip_bytes = real_s3_storage.get_object(storage_uri=result.zip_storage_uri)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            files = zf.namelist()

            # Should have content_list.json (SSOT §2.3 priority 1)
            content_list_files = [f for f in files if "_content_list.json" in f]
            assert len(content_list_files) >= 1, "Missing content_list.json"

            # Should have full.md (SSOT §2.3 priority 3)
            md_files = [f for f in files if f == "full.md" or f.endswith("/full.md")]
            assert len(md_files) >= 1, "Missing full.md"

            print(f"\n=== Zip Structure ===")
            print(f"Total files: {len(files)}")
            print(f"Content list files: {content_list_files}")
            print(f"Markdown files: {md_files}")

            # Print all files for debugging
            print("\nAll files in zip:")
            for f in sorted(files)[:20]:
                print(f"  {f}")
            if len(files) > 20:
                print(f"  ... and {len(files) - 20} more")

    def test_images_saved_to_minio(
        self,
        real_service,
        real_s3_storage,
    ):
        """Test that images are extracted and saved to MinIO."""
        import time

        doc_id = f"doc_images_{int(time.time())}"
        job_id = f"job_images_{int(time.time())}"

        result = real_service.parse_and_persist(
            file_url="https://arxiv.org/pdf/2305.12002.pdf",
            document_id=doc_id,
            tenant_id="tenant_real_test",
            job_id=job_id,
        )

        print(f"\n=== Image Storage Test ===")
        print(f"Images count: {result.images_count}")
        print(f"Images URIs: {result.images_storage_uris}")

        if result.images_storage_uris:
            for uri in result.images_storage_uris[:5]:
                # Verify image can be retrieved
                img_bytes = real_s3_storage.get_object(storage_uri=uri)
                print(f"  {uri.split('/')[-1]}: {len(img_bytes)} bytes")

                # Verify image URI format
                # Expected: object://s3/bea/tenants/{tenant_id}/document_parse/{doc_id}/images/{filename}
                assert "images" in uri, f"Image URI missing 'images' path: {uri}"

    def test_error_handling_and_manifest_update(
        self,
        real_service,
        real_manifests_repo,
    ):
        """Test that errors are properly recorded in manifest."""
        from app.errors import ApiError
        import time

        doc_id = f"doc_error_{int(time.time())}"
        job_id = f"job_error_{int(time.time())}"

        with pytest.raises(ApiError):
            real_service.parse_and_persist(
                file_url="https://example.com/nonexistent_document_12345.pdf",
                document_id=doc_id,
                tenant_id="tenant_real_test",
                job_id=job_id,
            )

        # Verify manifest shows failure
        manifest = real_manifests_repo.get(tenant_id="tenant_real_test", job_id=job_id)
        assert manifest is not None
        assert manifest["status"] == "failed"
        assert manifest["error_code"] is not None

        print(f"\n=== Error Handling ===")
        print(f"Status: {manifest['status']}")
        print(f"Error code: {manifest['error_code']}")


@pytest.mark.real_mineru
@pytest.mark.integration
class TestMinIOConnectivity:
    """Test MinIO connectivity without MinerU API."""

    def test_minio_bucket_exists(self, real_s3_storage):
        """Verify MinIO bucket is accessible."""
        # Try to put and get an object
        test_uri = real_s3_storage.put_object(
            tenant_id="tenant_test",
            object_type="test",
            object_id="connectivity",
            filename="test.txt",
            content_bytes=b"MinIO connectivity test",
            content_type="text/plain",
        )

        assert test_uri.startswith("object://s3/")

        # Retrieve the object
        content = real_s3_storage.get_object(storage_uri=test_uri)
        assert content == b"MinIO connectivity test"

        print(f"\n=== MinIO Connectivity ===")
        print(f"Test URI: {test_uri}")
        print(f"Content: {content}")

    def test_presigned_url_generation(self, real_s3_storage):
        """Test presigned URL generation for S3 backend."""
        # Put an object
        test_uri = real_s3_storage.put_object(
            tenant_id="tenant_test",
            object_type="test",
            object_id="presigned",
            filename="test.pdf",
            content_bytes=b"%PDF-1.4 test content",
            content_type="application/pdf",
        )

        # Generate presigned URL
        presigned_url = real_s3_storage.get_presigned_url(
            storage_uri=test_uri,
            expires_in=3600,
        )

        assert presigned_url is not None
        assert "http://localhost:9000" in presigned_url

        print(f"\n=== Presigned URL ===")
        print(f"URI: {test_uri}")
        print(f"URL: {presigned_url[:100]}...")


@pytest.mark.real_mineru
@pytest.mark.integration
class TestPostgreSQLConnectivity:
    """Test PostgreSQL connectivity without MinerU API."""

    def test_postgres_connection(self, real_postgres_connection):
        """Verify PostgreSQL is accessible."""
        with real_postgres_connection.cursor() as cur:
            cur.execute("SELECT 1 as test")
            row = cur.fetchone()
            assert row["test"] == 1

        print("\n=== PostgreSQL Connectivity ===")
        print("Connection: OK")

    def test_parse_manifests_table(self, real_manifests_repo):
        """Test parse_manifests table operations."""
        import time

        job_id = f"job_test_{int(time.time())}"

        # Insert
        manifest = real_manifests_repo.upsert(
            tenant_id="tenant_test",
            manifest={
                "job_id": job_id,
                "document_id": "doc_test",
                "selected_parser": "mineru",
                "parser_version": "v1",
                "status": "testing",
                "error_code": None,
            },
        )

        # Retrieve
        retrieved = real_manifests_repo.get(tenant_id="tenant_test", job_id=job_id)
        assert retrieved is not None
        assert retrieved["status"] == "testing"

        print(f"\n=== Parse Manifests Table ===")
        print(f"Job ID: {job_id}")
        print(f"Status: {retrieved['status']}")

    def test_document_chunks_table(self, real_documents_repo):
        """Test document_chunks table operations."""
        import time

        doc_id = f"doc_test_{int(time.time())}"

        # Insert chunks
        chunks = real_documents_repo.replace_chunks(
            tenant_id="tenant_test",
            document_id=doc_id,
            chunks=[
                {
                    "chunk_id": f"ck_{doc_id}_1",
                    "chunk_hash": "abc123",
                    "pages": [1],
                    "positions": [{"page": 1, "bbox": [0, 0, 1, 1], "start": 0, "end": 10}],
                    "section": "test",
                    "heading_path": ["test"],
                    "chunk_type": "text",
                    "parser": "mineru",
                    "parser_version": "v1",
                    "text": "Test chunk content",
                },
            ],
        )

        # Retrieve chunks
        retrieved = real_documents_repo.get_chunks(
            tenant_id="tenant_test",
            document_id=doc_id,
        )
        assert len(retrieved) == 1
        assert retrieved[0]["text"] == "Test chunk content"

        print(f"\n=== Document Chunks Table ===")
        print(f"Document ID: {doc_id}")
        print(f"Chunks: {len(retrieved)}")
