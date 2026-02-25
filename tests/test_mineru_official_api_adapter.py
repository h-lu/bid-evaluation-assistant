"""Tests for MinerU Official API Adapter.

These tests verify the adapter implementation and SSOT alignment.
Integration tests that call the real API are in test_mineru_official_api.py.
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from app.errors import ApiError
from app.mineru_official_api import (
    MineruApiConfig,
    MineruContentItem,
    MineruOfficialApiAdapter,
    MineruOfficialApiClient,
)


class TestMineruContentItem:
    """Test MineruContentItem aligns with SSOT §5.1."""

    def test_from_dict_with_all_fields(self):
        """Parse complete content item."""
        data = {
            "type": "text",
            "text": "Hello World",
            "page_idx": 0,
            "bbox": [100, 200, 300, 400],
            "text_level": 1,
        }
        item = MineruContentItem.from_dict(data)

        assert item.text == "Hello World"
        assert item.type == "text"
        assert item.page_idx == 0
        assert item.bbox == [100, 200, 300, 400]  # Already normalized
        assert item.text_level == 1

    def test_from_dict_normalizes_bbox(self):
        """Bbox should be normalized per SSOT §5.2."""
        data = {
            "type": "text",
            "text": "Test",
            "page_idx": 0,
            "bbox": [0.1, 0.2, 0.9, 0.8],  # Already normalized ratio
        }
        item = MineruContentItem.from_dict(data)

        # Should pass through normalize_bbox
        assert len(item.bbox) == 4

    def test_from_dict_handles_missing_fields(self):
        """Handle missing optional fields gracefully."""
        data = {
            "text": "Just text",
        }
        item = MineruContentItem.from_dict(data)

        assert item.text == "Just text"
        assert item.type == "text"  # Default
        assert item.page_idx == 0  # Default
        assert item.bbox == [0.0, 0.0, 1.0, 1.0]  # Default full page

    def test_to_chunk_dict_format(self):
        """Output chunk should match expected format."""
        item = MineruContentItem(
            text="Sample content",
            type="text",
            page_idx=2,
            bbox=[50, 100, 200, 300],
            text_level=2,
        )

        chunk = item.to_chunk_dict(
            document_id="doc_123",
            parser="mineru_official",
            parser_version="v1",
            section="test_section",
            heading_path=["h2", "Sample content"],
        )

        # Verify chunk structure
        assert chunk["document_id"] == "doc_123"
        assert chunk["pages"] == [3]  # page_idx + 1
        assert chunk["positions"][0]["page"] == 3
        assert chunk["positions"][0]["bbox"] == [50, 100, 200, 300]
        assert chunk["parser"] == "mineru_official"
        assert chunk["parser_version"] == "v1"
        assert chunk["text"] == "Sample content"


class TestMineruOfficialApiClient:
    """Test low-level API client."""

    @pytest.fixture
    def config(self):
        return MineruApiConfig(
            api_key="test_key_123",
            api_base="https://test.api",
            timeout_s=10.0,
            poll_interval_s=1.0,
            max_poll_time_s=30.0,
        )

    @pytest.fixture
    def client(self, config):
        return MineruOfficialApiClient(config)

    def test_config_defaults(self):
        """Test default configuration values."""
        config = MineruApiConfig(api_key="key")

        assert config.api_base == "https://mineru.net/api/v4"
        assert config.timeout_s == 30.0
        assert config.poll_interval_s == 5.0
        assert config.max_poll_time_s == 180.0
        assert config.is_ocr is True
        assert config.enable_formula is False

    def test_submit_task_success(self, client):
        """Test successful task submission."""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {
                "code": 0,
                "data": {"task_id": "task_abc123"},
            }

            task_id = client.submit_task(file_url="https://example.com/test.pdf")

            assert task_id == "task_abc123"
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["endpoint"] == "/extract/task"
            assert call_args.kwargs["method"] == "POST"

    def test_submit_task_retry_limit_error(self, client):
        """Test retry limit error is permanent."""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {
                "code": -1,
                "msg": "retry limit reached (5 attempts)",
            }

            with pytest.raises(ApiError) as exc:
                client.submit_task(file_url="https://example.com/test.pdf")

            assert exc.value.code == "MINERU_RETRY_LIMIT_REACHED"
            assert not exc.value.retryable

    def test_poll_until_complete_success(self, client):
        """Test successful polling."""
        with patch.object(client, "get_task_status") as mock_status:
            # First call: processing, second call: done
            mock_status.side_effect = [
                {"state": "processing"},
                {"state": "done", "full_zip_url": "https://cdn.example.com/result.zip"},
            ]

            zip_url = client.poll_until_complete(task_id="task_123")

            assert zip_url == "https://cdn.example.com/result.zip"
            assert mock_status.call_count == 2

    def test_poll_until_complete_failure(self, client):
        """Test task failure during polling."""
        with patch.object(client, "get_task_status") as mock_status:
            mock_status.return_value = {
                "state": "failed",
                "err_msg": "PDF corrupted",
            }

            with pytest.raises(ApiError) as exc:
                client.poll_until_complete(task_id="task_123")

            assert exc.value.code == "DOC_PARSE_UPSTREAM_ERROR"

    def test_poll_until_complete_timeout(self, client):
        """Test polling timeout."""
        client._config.max_poll_time_s = 0.1  # Very short timeout

        with patch.object(client, "get_task_status") as mock_status:
            mock_status.return_value = {"state": "processing"}

            with pytest.raises(ApiError) as exc:
                client.poll_until_complete(task_id="task_123")

            assert exc.value.code == "DOC_PARSE_TIMEOUT"


class TestMineruOfficialApiAdapter:
    """Test the high-level adapter."""

    @pytest.fixture
    def config(self):
        return MineruApiConfig(
            api_key="test_key",
            timeout_s=10.0,
            max_poll_time_s=30.0,
        )

    @pytest.fixture
    def adapter(self, config):
        return MineruOfficialApiAdapter(config=config, name="mineru_official", version="v1")

    def test_extract_content_list_priority(self, adapter):
        """Content list extraction follows SSOT §2.3 priority."""
        content = {
            "output_content_list.json": json.dumps([
                {"text": "priority 1", "type": "text", "page_idx": 0, "bbox": [0, 0, 100, 100]}
            ]),
            "context_list.json": json.dumps([
                {"text": "priority 2", "type": "text", "page_idx": 0, "bbox": [0, 0, 100, 100]}
            ]),
        }

        items = adapter._extract_content_list(content)

        # Should prefer *_content_list.json
        assert len(items) == 1
        assert items[0].text == "priority 1"

    def test_extract_content_list_fallback_to_context(self, adapter):
        """Fallback to context_list.json if no content_list."""
        content = {
            "context_list.json": json.dumps([
                {"text": "fallback", "type": "text", "page_idx": 0, "bbox": [0, 0, 100, 100]}
            ]),
        }

        items = adapter._extract_content_list(content)

        assert len(items) == 1
        assert items[0].text == "fallback"

    def test_extract_full_md_priority(self, adapter):
        """Full.md extraction follows SSOT §2.3 priority."""
        content = {
            "full.md": "# Priority 1\nContent here",
            "other.md": "# Priority 2\nOther content",
        }

        result = adapter._extract_full_md(content)

        assert result == "# Priority 1\nContent here"

    def test_extract_full_md_fallback(self, adapter):
        """Fallback to any .md file if no full.md."""
        content = {
            "other.md": "# Fallback\nContent",
        }

        result = adapter._extract_full_md(content)

        assert result == "# Fallback\nContent"

    def test_build_heading_path_with_text_level(self, adapter):
        """Heading path built from text_level."""
        item = MineruContentItem(
            text="Section Title",
            type="text",
            page_idx=0,
            bbox=[0, 0, 100, 100],
            text_level=2,
        )

        path = adapter._build_heading_path(item, None)

        assert path == ["h2", "Section Title"]

    def test_parse_from_url_full_flow(self, adapter):
        """Test complete parsing flow."""
        mock_client = MagicMock()
        mock_client.submit_task.return_value = "task_123"
        mock_client.poll_until_complete.return_value = "https://cdn.example.com/result.zip"
        mock_client.download_and_extract_zip.return_value = {
            "output_content_list.json": json.dumps([
                {"text": "Extracted text", "type": "text", "page_idx": 0, "bbox": [100, 200, 300, 400], "text_level": 1}
            ]),
            "full.md": "# Document\nExtracted text",
        }
        adapter._client = mock_client

        result = adapter.parse_from_url(
            file_url="https://example.com/test.pdf",
            document_id="doc_123",
        )

        assert result["document_id"] == "doc_123"
        assert result["text"] == "Extracted text"
        assert result["parser"] == "mineru_official"
        assert result["pages"] == [1]

    def test_parse_from_url_fallback_to_full_md(self, adapter):
        """Fallback to full.md if no content_list."""
        mock_client = MagicMock()
        mock_client.submit_task.return_value = "task_123"
        mock_client.poll_until_complete.return_value = "https://cdn.example.com/result.zip"
        mock_client.download_and_extract_zip.return_value = {
            "full.md": "# Document\nThis is the content from markdown.",
        }
        adapter._client = mock_client

        result = adapter.parse_from_url(
            file_url="https://example.com/test.pdf",
            document_id="doc_456",
        )

        assert result["document_id"] == "doc_456"
        assert "content from markdown" in result["text"]
        assert result["content_source"] == "mineru_full_md"

    def test_parse_from_url_no_content_raises_error(self, adapter):
        """Raise error if no parseable content."""
        mock_client = MagicMock()
        mock_client.submit_task.return_value = "task_123"
        mock_client.poll_until_complete.return_value = "https://cdn.example.com/result.zip"
        mock_client.download_and_extract_zip.return_value = {}  # Empty
        adapter._client = mock_client

        with pytest.raises(ApiError) as exc:
            adapter.parse_from_url(
                file_url="https://example.com/test.pdf",
                document_id="doc_789",
            )

        assert exc.value.code == "DOC_PARSE_OUTPUT_NOT_FOUND"


class TestGetMineruOfficialAdapter:
    """Test factory function for adapter."""

    def test_returns_none_without_api_key(self):
        """Returns None if MINERU_API_KEY not set."""
        from app.parser_adapters import get_mineru_official_adapter

        adapter = get_mineru_official_adapter(env={"MINERU_API_KEY": ""})

        assert adapter is None

    def test_returns_adapter_with_api_key(self):
        """Returns adapter if MINERU_API_KEY is set."""
        from app.parser_adapters import get_mineru_official_adapter

        adapter = get_mineru_official_adapter(env={"MINERU_API_KEY": "test_key_123"})

        assert adapter is not None
        assert adapter.name == "mineru_official"

    def test_uses_env_config(self):
        """Adapter uses environment configuration."""
        from app.parser_adapters import get_mineru_official_adapter

        adapter = get_mineru_official_adapter(env={
            "MINERU_API_KEY": "key",
            "MINERU_TIMEOUT_S": "60",
            "MINERU_MAX_POLL_TIME_S": "300",
            "MINERU_IS_OCR": "false",
            "MINERU_ENABLE_FORMULA": "true",
        })

        assert adapter is not None
        assert adapter._config.timeout_s == 60.0
        assert adapter._config.max_poll_time_s == 300.0
        assert adapter._config.is_ocr is False
        assert adapter._config.enable_formula is True
