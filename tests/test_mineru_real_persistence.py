"""Real MinerU API persistence tests.

These tests use the real MinerU Official API and require MINERU_API_KEY.

Run with: pytest tests/test_mineru_real_persistence.py -v -m real_mineru

To skip these tests (default): pytest -v -m "not real_mineru"
"""
from __future__ import annotations

import json
import os
import pytest
from datetime import datetime
from unittest.mock import patch

# Skip all tests in this module if MINERU_API_KEY not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("MINERU_API_KEY", "").strip(),
    reason="MINERU_API_KEY not set - run with -m real_mineru to include",
)


class MockObjectStorage:
    """Real file-backed object storage for persistence testing."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.objects: dict[str, bytes] = {}
        os.makedirs(base_dir, exist_ok=True)

    def put_object(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str | None = None,
    ) -> str:
        key = f"object://local/bea/tenants/{tenant_id}/{object_type}/{object_id}/{filename}"
        self.objects[key] = content_bytes

        # Also write to disk for persistence verification
        file_path = os.path.join(
            self.base_dir,
            tenant_id,
            object_type,
            object_id,
            filename,
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content_bytes)

        return key

    def get_object(self, *, storage_uri: str) -> bytes:
        return self.objects.get(storage_uri, b"")

    def list_objects(self, *, tenant_id: str, object_type: str, object_id: str) -> list[str]:
        """List all objects for a given tenant/type/id."""
        prefix = f"object://local/bea/tenants/{tenant_id}/{object_type}/{object_id}/"
        return [k for k in self.objects.keys() if k.startswith(prefix)]


class MockParseManifestsRepo:
    """Mock parse manifests repository."""

    def __init__(self):
        self.manifests: dict[str, dict] = {}

    def upsert(self, *, tenant_id: str, manifest: dict) -> dict:
        key = manifest.get("job_id", "unknown")
        self.manifests[key] = dict(manifest)
        self.manifests[key]["tenant_id"] = tenant_id
        return self.manifests[key]

    def get(self, *, tenant_id: str, job_id: str) -> dict | None:
        manifest = self.manifests.get(job_id)
        if manifest and manifest.get("tenant_id") == tenant_id:
            return manifest
        return None


class MockDocumentsRepo:
    """Mock documents repository."""

    def __init__(self):
        self.documents: dict[str, dict] = {}
        self.chunks: dict[str, list[dict]] = {}

    def upsert_document(self, *, document: dict) -> dict:
        doc_id = document.get("document_id", "unknown")
        self.documents[doc_id] = dict(document)
        return self.documents[doc_id]

    def get(self, *, tenant_id: str, document_id: str) -> dict | None:
        doc = self.documents.get(document_id)
        if doc and doc.get("tenant_id") == tenant_id:
            return doc
        return None

    def replace_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict],
    ) -> list[dict]:
        key = f"{tenant_id}:{document_id}"
        self.chunks[key] = [dict(c) for c in chunks]
        return self.chunks[key]


@pytest.fixture
def real_storage(tmp_path):
    """Create real file-backed storage."""
    return MockObjectStorage(base_dir=str(tmp_path / "objects"))


@pytest.fixture
def manifests_repo():
    return MockParseManifestsRepo()


@pytest.fixture
def documents_repo():
    return MockDocumentsRepo()


@pytest.fixture
def real_service(real_storage, manifests_repo, documents_repo):
    """Create service with real storage."""
    from app.mineru_parse_service import build_mineru_parse_service

    service = build_mineru_parse_service(
        object_storage=real_storage,
        parse_manifests_repo=manifests_repo,
        documents_repo=documents_repo,
    )
    assert service is not None, "MINERU_API_KEY required for real tests"
    return service


@pytest.mark.real_mineru
@pytest.mark.slow
class TestRealMineruPersistence:
    """Real persistence tests with MinerU Official API."""

    def test_full_parse_and_persist_flow(self, real_service, real_storage, manifests_repo, documents_repo):
        """Test complete parse and persist flow with real MinerU API.

        Verifies:
        1. Zip saved to object storage
        2. Images saved to object storage
        3. Manifest updated with success status
        4. Chunks persisted with correct fields
        """
        result = real_service.parse_and_persist(
            file_url="https://arxiv.org/pdf/2305.12002.pdf",
            document_id="doc_real_test_001",
            tenant_id="tenant_test",
            job_id="job_real_test_001",
        )

        # Verify result
        assert result.status == "completed"
        assert result.document_id == "doc_real_test_001"
        assert result.job_id == "job_real_test_001"
        assert result.chunks_count > 0
        assert result.zip_storage_uri is not None
        assert result.full_md is not None

        # Verify zip saved
        assert result.zip_storage_uri in real_storage.objects
        zip_bytes = real_storage.objects[result.zip_storage_uri]
        assert len(zip_bytes) > 0
        assert zip_bytes[:4] == b"PK\x03\x04"  # ZIP magic bytes

        # Verify images saved (if any)
        image_uris = real_storage.list_objects(
            tenant_id="tenant_test",
            object_type="document_parse",
            object_id="doc_real_test_001",
        )
        image_uris = [u for u in image_uris if "/images/" in u]
        if image_uris:
            print(f"\nSaved {len(image_uris)} images:")
            for uri in image_uris:
                img_bytes = real_storage.objects.get(uri, b"")
                print(f"  {uri.split('/')[-1]}: {len(img_bytes)} bytes")

        # Verify manifest
        manifest = manifests_repo.get(tenant_id="tenant_test", job_id="job_real_test_001")
        assert manifest is not None
        assert manifest["status"] == "completed"
        assert manifest["error_code"] is None

        # Verify chunks persisted
        chunks = documents_repo.chunks.get("tenant_test:doc_real_test_001", [])
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

        print(f"\n=== Parse Result ===")
        print(f"Status: {result.status}")
        print(f"Chunks: {result.chunks_count}")
        print(f"Parse time: {result.parse_time_s:.2f}s")
        print(f"Zip size: {len(zip_bytes)} bytes")
        print(f"Full.md length: {len(result.full_md or '')} chars")

    def test_parse_result_zip_structure(self, real_service, real_storage):
        """Verify the saved zip has correct structure."""
        import zipfile
        import io

        result = real_service.parse_and_persist(
            file_url="https://arxiv.org/pdf/2305.12002.pdf",
            document_id="doc_zip_structure_test",
            tenant_id="tenant_test",
            job_id="job_zip_structure_test",
        )

        zip_bytes = real_storage.objects[result.zip_storage_uri]
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            files = zf.namelist()

            # Should have content_list.json
            content_list_files = [f for f in files if "_content_list.json" in f]
            assert len(content_list_files) >= 1, "Missing content_list.json"

            # Should have full.md
            md_files = [f for f in files if f == "full.md" or f.endswith("/full.md")]
            assert len(md_files) >= 1, "Missing full.md"

            # May have images directory
            image_files = [f for f in files if f.startswith("images/")]
            print(f"\nFiles in zip: {len(files)}")
            print(f"  Content list: {len(content_list_files)}")
            print(f"  Markdown: {len(md_files)}")
            print(f"  Images: {len(image_files)}")

    def test_images_extracted_and_saved(self, real_service, real_storage):
        """Test that images are extracted from zip and saved separately."""
        result = real_service.parse_and_persist(
            file_url="https://arxiv.org/pdf/2305.12002.pdf",
            document_id="doc_image_test",
            tenant_id="tenant_test",
            job_id="job_image_test",
        )

        # Check for saved images
        all_objects = real_storage.list_objects(
            tenant_id="tenant_test",
            object_type="document_parse",
            object_id="doc_image_test",
        )

        # Filter for image objects
        image_objects = [u for u in all_objects if "/images/" in u]

        print(f"\n=== Image Storage ===")
        print(f"Total objects: {len(all_objects)}")
        print(f"Image objects: {len(image_objects)}")

        if image_objects:
            for uri in image_objects[:5]:  # Show first 5
                img_bytes = real_storage.objects.get(uri, b"")
                filename = uri.split("/")[-1]
                print(f"  {filename}: {len(img_bytes)} bytes")

        # Verify image URIs are returned in result (if any)
        if image_objects:
            assert result.images_storage_uris is not None
            assert len(result.images_storage_uris) > 0


@pytest.mark.real_mineru
@pytest.mark.slow
class TestRealMineruErrorHandling:
    """Test error handling with real MinerU API."""

    def test_invalid_url_returns_proper_error(self, real_service, manifests_repo):
        """Test that invalid URL returns proper error."""
        from app.errors import ApiError

        with pytest.raises(ApiError) as exc_info:
            real_service.parse_and_persist(
                file_url="https://example.com/nonexistent.pdf",
                document_id="doc_error_test",
                tenant_id="tenant_test",
                job_id="job_error_test",
            )

        # Verify manifest shows failure
        manifest = manifests_repo.get(tenant_id="tenant_test", job_id="job_error_test")
        assert manifest is not None
        assert manifest["status"] == "failed"
        assert manifest["error_code"] is not None
