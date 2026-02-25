"""Tests for MinerU Parse Service with Persistence."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.errors import ApiError
from app.mineru_official_api import MineruApiConfig, MineruContentItem
from app.mineru_parse_service import (
    MineruParseResult,
    MineruParseService,
    build_mineru_parse_service,
)


class MockObjectStorage:
    """Mock object storage for testing."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

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
        return key

    def get_object(self, *, storage_uri: str) -> bytes:
        return self.objects.get(storage_uri, b"")


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
def config():
    return MineruApiConfig(
        api_key="test_key",
        timeout_s=10.0,
        max_poll_time_s=30.0,
    )


@pytest.fixture
def object_storage():
    return MockObjectStorage()


@pytest.fixture
def manifests_repo():
    return MockParseManifestsRepo()


@pytest.fixture
def documents_repo():
    return MockDocumentsRepo()


@pytest.fixture
def service(config, object_storage, manifests_repo, documents_repo):
    return MineruParseService(
        config=config,
        object_storage=object_storage,
        parse_manifests_repo=manifests_repo,
        documents_repo=documents_repo,
    )


def _make_test_zip() -> bytes:
    """Create a test zip with content_list.json and full.md."""
    import io
    import zipfile

    content_list = [
        {
            "type": "text",
            "text": "Title of Document",
            "page_idx": 0,
            "bbox": [100, 200, 500, 250],
            "text_level": 1,
        },
        {
            "type": "text",
            "text": "This is the first paragraph of the document.",
            "page_idx": 0,
            "bbox": [100, 300, 500, 400],
        },
    ]

    full_md = "# Title of Document\n\nThis is the first paragraph of the document.\n"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc_content_list.json", json.dumps(content_list))
        zf.writestr("full.md", full_md)

    return buf.getvalue()


class TestMineruParseService:
    """Test MinerU parse service."""

    def test_service_initialization(self, service):
        """Service should initialize correctly."""
        assert service._config.api_key == "test_key"
        assert service._object_storage is not None
        assert service._parse_manifests_repo is not None
        assert service._documents_repo is not None

    def test_parse_and_persist_full_flow(self, service, object_storage, manifests_repo, documents_repo):
        """Test complete parse and persist flow."""
        # Mock the client methods
        mock_client = MagicMock()
        mock_client.submit_task.return_value = "task_123"
        mock_client.poll_until_complete.return_value = "https://cdn.example.com/result.zip"

        # Mock download to return our test zip
        test_zip = _make_test_zip()

        with (
            patch.object(service, "_client", mock_client),
            patch.object(service, "_download_zip", return_value=test_zip),
        ):
            result = service.parse_and_persist(
                file_url="https://example.com/test.pdf",
                document_id="doc_123",
                tenant_id="tenant_abc",
                job_id="job_xyz",
            )

        # Verify result
        assert result.document_id == "doc_123"
        assert result.job_id == "job_xyz"
        assert result.status == "completed"
        assert result.chunks_count == 2
        assert result.zip_storage_uri is not None
        assert result.full_md is not None

        # Verify zip saved to object storage
        assert result.zip_storage_uri in object_storage.objects

        # Verify manifest updated
        manifest = manifests_repo.get(tenant_id="tenant_abc", job_id="job_xyz")
        assert manifest is not None
        assert manifest["status"] == "completed"

        # Verify chunks persisted
        chunks_key = "tenant_abc:doc_123"
        assert chunks_key in documents_repo.chunks
        assert len(documents_repo.chunks[chunks_key]) == 2

    def test_parse_persists_content_list_items(self, service, object_storage, manifests_repo, documents_repo):
        """Content list items should be converted to chunks with correct fields."""
        mock_client = MagicMock()
        mock_client.submit_task.return_value = "task_123"
        mock_client.poll_until_complete.return_value = "https://cdn.example.com/result.zip"
        test_zip = _make_test_zip()

        with (
            patch.object(service, "_client", mock_client),
            patch.object(service, "_download_zip", return_value=test_zip),
        ):
            service.parse_and_persist(
                file_url="https://example.com/test.pdf",
                document_id="doc_123",
                tenant_id="tenant_abc",
                job_id="job_xyz",
            )

        chunks = documents_repo.chunks.get("tenant_abc:doc_123", [])
        assert len(chunks) == 2

        # Check first chunk (title)
        title_chunk = chunks[0]
        assert title_chunk["chunk_type"] == "text"
        assert title_chunk["text"] == "Title of Document"
        assert title_chunk["pages"] == [1]  # 1-indexed
        assert title_chunk["heading_path"] == ["h1", "Title of Document"]
        assert title_chunk["parser"] == "mineru_official"

        # Check second chunk (paragraph)
        para_chunk = chunks[1]
        assert para_chunk["text"] == "This is the first paragraph of the document."
        assert para_chunk["heading_path"] == ["content"]

    def test_parse_updates_manifest_on_failure(self, service, manifests_repo):
        """Manifest should be updated with error on parse failure."""
        mock_client = MagicMock()
        mock_client.submit_task.side_effect = ApiError(
            code="DOC_PARSE_UPSTREAM_UNAVAILABLE",
            message="MinerU API unavailable",
            error_class="transient",
            retryable=True,
            http_status=503,
        )

        with patch.object(service, "_client", mock_client), pytest.raises(ApiError):
            service.parse_and_persist(
                file_url="https://example.com/test.pdf",
                document_id="doc_123",
                tenant_id="tenant_abc",
                job_id="job_xyz",
            )

        # Verify manifest shows failure
        manifest = manifests_repo.get(tenant_id="tenant_abc", job_id="job_xyz")
        assert manifest is not None
        assert manifest["status"] == "failed"
        assert manifest["error_code"] == "DOC_PARSE_UPSTREAM_UNAVAILABLE"

    def test_compute_chunk_hash_is_deterministic(self, service):
        """Chunk hash should be deterministic."""
        hash1 = service._compute_chunk_hash(
            document_id="doc_123",
            page_idx=0,
            bbox=[100, 200, 300, 400],
            text="Test text",
        )
        hash2 = service._compute_chunk_hash(
            document_id="doc_123",
            page_idx=0,
            bbox=[100, 200, 300, 400],
            text="Test text",
        )
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_compute_chunk_hash_differs_by_content(self, service):
        """Different content should produce different hashes."""
        hash1 = service._compute_chunk_hash(
            document_id="doc_123",
            page_idx=0,
            bbox=[100, 200, 300, 400],
            text="Test text 1",
        )
        hash2 = service._compute_chunk_hash(
            document_id="doc_123",
            page_idx=0,
            bbox=[100, 200, 300, 400],
            text="Test text 2",
        )
        assert hash1 != hash2

    def test_build_heading_path_with_text_level(self, service):
        """Heading path should be built from text_level."""
        item = MineruContentItem(
            text="Section Title",
            type="text",
            page_idx=0,
            bbox=[0, 0, 100, 100],
            text_level=2,
        )

        path = service._build_heading_path(item, None)
        assert path == ["h2", "Section Title"]

    def test_build_heading_path_without_text_level(self, service):
        """Heading path should default to content without text_level."""
        item = MineruContentItem(
            text="Paragraph text",
            type="text",
            page_idx=0,
            bbox=[0, 0, 100, 100],
            text_level=None,
        )

        path = service._build_heading_path(item, None)
        assert path == ["content"]

    def test_infer_section_from_text_level(self, service):
        """Section should be inferred from text_level."""
        item_h1 = MineruContentItem(text="Title", type="text", page_idx=0, bbox=[0, 0, 1, 1], text_level=1)
        item_h2 = MineruContentItem(text="Section", type="text", page_idx=0, bbox=[0, 0, 1, 1], text_level=2)
        item_none = MineruContentItem(text="Para", type="text", page_idx=0, bbox=[0, 0, 1, 1], text_level=None)

        assert service._infer_section(item_h1, None) == "title"
        assert service._infer_section(item_h2, None) == "section"
        assert service._infer_section(item_none, None) == "content"

    def test_save_images_extracts_and_persists_images(self, service, object_storage):
        """Images should be extracted from zip and saved to object storage."""
        import io
        import zipfile

        # Create a test zip with images
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("images/test_image.jpg", b"\xff\xd8\xff\xe0test_jpeg_data")
            zf.writestr("images/nested/deep.png", b"\x89PNGtest_png_data")
            zf.writestr("full.md", "# Test")

        zip_bytes = buf.getvalue()

        # Call _save_images
        uris = service._save_images(
            tenant_id="tenant_test",
            document_id="doc_test",
            zip_bytes=zip_bytes,
        )

        # Verify URIs returned
        assert len(uris) == 2
        assert any("test_image.jpg" in uri for uri in uris)
        assert any("deep.png" in uri for uri in uris)

        # Verify images saved to storage
        for uri in uris:
            assert uri in object_storage.objects
            assert len(object_storage.objects[uri]) > 0

    def test_save_images_handles_empty_zip(self, service):
        """Empty zip should return empty list."""
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("full.md", "# Test")

        zip_bytes = buf.getvalue()

        uris = service._save_images(
            tenant_id="tenant_test",
            document_id="doc_test",
            zip_bytes=zip_bytes,
        )

        assert uris == []

    def test_save_images_handles_no_images_directory(self, service):
        """Zip without images directory should return empty list."""
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("full.md", "# Test")
            zf.writestr("other.txt", "text")

        zip_bytes = buf.getvalue()

        uris = service._save_images(
            tenant_id="tenant_test",
            document_id="doc_test",
            zip_bytes=zip_bytes,
        )

        assert uris == []


class TestBuildMineruParseService:
    """Test factory function."""

    def test_returns_none_without_api_key(self):
        """Returns None if MINERU_API_KEY not set."""
        result = build_mineru_parse_service(
            object_storage=MockObjectStorage(),
            parse_manifests_repo=MockParseManifestsRepo(),
            documents_repo=MockDocumentsRepo(),
            env={"MINERU_API_KEY": ""},
        )
        assert result is None

    def test_returns_service_with_api_key(self):
        """Returns service if MINERU_API_KEY is set."""
        result = build_mineru_parse_service(
            object_storage=MockObjectStorage(),
            parse_manifests_repo=MockParseManifestsRepo(),
            documents_repo=MockDocumentsRepo(),
            env={"MINERU_API_KEY": "test_key"},
        )
        assert result is not None
        assert isinstance(result, MineruParseService)

    def test_uses_env_config(self):
        """Service uses environment configuration."""
        result = build_mineru_parse_service(
            object_storage=MockObjectStorage(),
            parse_manifests_repo=MockParseManifestsRepo(),
            documents_repo=MockDocumentsRepo(),
            env={
                "MINERU_API_KEY": "key",
                "MINERU_TIMEOUT_S": "60",
                "MINERU_MAX_POLL_TIME_S": "300",
                "MINERU_IS_OCR": "false",
                "MINERU_ENABLE_FORMULA": "true",
            },
        )
        assert result is not None
        assert result._config.timeout_s == 60.0
        assert result._config.max_poll_time_s == 300.0
        assert result._config.is_ocr is False
        assert result._config.enable_formula is True


class TestMineruParseResult:
    """Test MineruParseResult dataclass."""

    def test_result_dataclass(self):
        """Result should have all expected fields."""
        result = MineruParseResult(
            document_id="doc_123",
            job_id="job_xyz",
            status="completed",
            chunks_count=5,
            zip_storage_uri="object://local/bea/tenants/t1/document_parse/doc_123/result.zip",
            images_storage_uris=["object://.../img1.jpg"],
            images_count=1,
            content_list=[{"text": "test"}],
            full_md="# Test",
            parse_time_s=12.5,
        )

        assert result.document_id == "doc_123"
        assert result.status == "completed"
        assert result.chunks_count == 5
        assert result.images_count == 1
        assert result.parse_time_s == 12.5
