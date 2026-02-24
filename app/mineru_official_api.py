"""MinerU Official API Adapter.

Implements async task-based parsing with MinerU cloud API.
API Documentation: https://mineru.net/apiManage/docs

SSOT Alignment:
- §3 解析器路由: mineru as primary PDF parser
- §5 字段标准化: text, type, page_idx, bbox
- §10 错误码: DOC_PARSE_*, MINERU_*
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

from app.errors import ApiError
from app.parse_utils import normalize_bbox


MINERU_API_BASE = "https://mineru.net/api/v4"


@dataclass
class MineruApiConfig:
    """Configuration for MinerU Official API."""
    api_key: str
    api_base: str = MINERU_API_BASE
    timeout_s: float = 30.0
    poll_interval_s: float = 5.0
    max_poll_time_s: float = 180.0
    is_ocr: bool = True
    enable_formula: bool = False


@dataclass
class MineruContentItem:
    """MinerU content_list item aligned with SSOT §5.1."""
    text: str
    type: str
    page_idx: int
    bbox: list[float]  # [x0, y0, x1, y1] normalized
    text_level: int | None = None  # Optional: heading level

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MineruContentItem":
        """Create from MinerU API response item."""
        # SSOT §5.1: required fields
        text = str(data.get("text") or "")
        item_type = str(data.get("type") or "text")
        page_idx = int(data.get("page_idx") or 0)

        # SSOT §5.2: bbox normalization
        bbox = data.get("bbox", [0, 0, 1, 1])
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0, 0, 1, 1]
        bbox = normalize_bbox(bbox)

        text_level = data.get("text_level")
        if text_level is not None:
            text_level = int(text_level)

        return cls(
            text=text,
            type=item_type,
            page_idx=page_idx,
            bbox=bbox,
            text_level=text_level,
        )

    def to_chunk_dict(
        self,
        *,
        document_id: str,
        parser: str,
        parser_version: str,
        section: str,
        heading_path: list[str] | None = None,
    ) -> dict[str, object]:
        """Convert to chunk format expected by ParserAdapterRegistry."""
        if heading_path is None:
            heading_path = ["content"]

        return {
            "document_id": document_id,
            "pages": [self.page_idx + 1],  # Convert 0-indexed to 1-indexed
            "positions": [
                {
                    "page": self.page_idx + 1,
                    "bbox": self.bbox,
                    "start": 0,
                    "end": len(self.text),
                }
            ],
            "section": section,
            "heading_path": heading_path,
            "chunk_type": self.type,
            "parser": parser,
            "parser_version": parser_version,
            "content_source": "mineru_official_api",
            "text": self.text,
        }


class MineruOfficialApiClient:
    """Low-level client for MinerU Official API."""

    def __init__(self, config: MineruApiConfig) -> None:
        self._config = config

    def _make_request(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to MinerU API."""
        url = f"{self._config.api_base}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        req = request.Request(
            url,
            data=body,
            method=method,
            headers=headers,
        )

        timeout = timeout or self._config.timeout_s
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                error_data = json.loads(raw)
                raise ApiError(
                    code="DOC_PARSE_UPSTREAM_ERROR",
                    message=f"MinerU API error: {error_data.get('msg', raw)}",
                    error_class="transient",
                    retryable=True,
                    http_status=503,
                ) from e
            except json.JSONDecodeError:
                raise ApiError(
                    code="DOC_PARSE_UPSTREAM_ERROR",
                    message=f"MinerU API HTTP {e.code}: {raw[:200]}",
                    error_class="transient",
                    retryable=True,
                    http_status=503,
                ) from e
        except (URLError, OSError) as e:
            raise ApiError(
                code="DOC_PARSE_UPSTREAM_UNAVAILABLE",
                message=f"MinerU API unavailable: {e}",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from e

    def submit_task(
        self,
        *,
        file_url: str,
        page_ranges: str | None = None,
    ) -> str:
        """Submit extraction task. Returns task_id."""
        data: dict[str, Any] = {
            "url": file_url,
            "is_ocr": self._config.is_ocr,
            "enable_formula": self._config.enable_formula,
        }
        if page_ranges:
            data["page_ranges"] = page_ranges

        result = self._make_request(
            endpoint="/extract/task",
            method="POST",
            data=data,
            timeout=60.0,
        )

        if result.get("code") != 0:
            msg = result.get("msg", "Unknown error")
            if "retry limit" in str(msg).lower():
                raise ApiError(
                    code="MINERU_RETRY_LIMIT_REACHED",
                    message=f"MinerU retry limit reached for this file: {msg}",
                    error_class="permanent",
                    retryable=False,
                    http_status=400,
                )
            raise ApiError(
                code="DOC_PARSE_UPSTREAM_ERROR",
                message=f"MinerU task submission failed: {msg}",
                error_class="transient",
                retryable=True,
                http_status=503,
            )

        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            raise ApiError(
                code="DOC_PARSE_SCHEMA_INVALID",
                message="MinerU response missing task_id",
                error_class="transient",
                retryable=True,
                http_status=503,
            )

        return str(task_id)

    def get_task_status(self, *, task_id: str) -> dict[str, Any]:
        """Get task status and result."""
        result = self._make_request(
            endpoint=f"/extract/task/{task_id}",
            method="GET",
        )

        if result.get("code") != 0:
            raise ApiError(
                code="DOC_PARSE_UPSTREAM_ERROR",
                message=f"MinerU task status query failed: {result.get('msg')}",
                error_class="transient",
                retryable=True,
                http_status=503,
            )

        return result.get("data", {})

    def poll_until_complete(self, *, task_id: str) -> str:
        """Poll task until complete. Returns zip_url."""
        start_time = time.time()

        while time.time() - start_time < self._config.max_poll_time_s:
            data = self.get_task_status(task_id=task_id)
            state = data.get("state", "unknown")

            if state == "done":
                zip_url = data.get("full_zip_url")
                if not zip_url:
                    raise ApiError(
                        code="DOC_PARSE_OUTPUT_NOT_FOUND",
                        message="MinerU task completed but no zip_url returned",
                        error_class="transient",
                        retryable=True,
                        http_status=503,
                    )
                return str(zip_url)

            if state == "failed":
                err_msg = data.get("err_msg", "Unknown error")
                raise ApiError(
                    code="DOC_PARSE_UPSTREAM_ERROR",
                    message=f"MinerU task failed: {err_msg}",
                    error_class="transient",
                    retryable=True,
                    http_status=503,
                )

            time.sleep(self._config.poll_interval_s)

        raise ApiError(
            code="DOC_PARSE_TIMEOUT",
            message=f"MinerU task timed out after {self._config.max_poll_time_s}s",
            error_class="transient",
            retryable=True,
            http_status=503,
        )

    def download_and_extract_zip(self, *, zip_url: str) -> dict[str, str]:
        """Download zip and extract content files."""
        try:
            with request.urlopen(zip_url, timeout=60) as resp:
                zip_data = resp.read()
        except (URLError, OSError) as e:
            raise ApiError(
                code="DOC_PARSE_OUTPUT_NOT_FOUND",
                message=f"Failed to download MinerU result zip: {e}",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from e

        content: dict[str, str] = {}
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                for name in zf.namelist():
                    if name.endswith((".md", ".json", ".txt")):
                        content[name] = zf.read(name).decode("utf-8", errors="replace")
        except zipfile.BadZipFile as e:
            raise ApiError(
                code="DOC_PARSE_SCHEMA_INVALID",
                message=f"MinerU result zip is corrupted: {e}",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from e

        return content


class MineruOfficialApiAdapter:
    """Parser adapter for MinerU Official API.

    Usage:
        adapter = MineruOfficialApiAdapter(config=config)
        result = adapter.parse_from_url(
            file_url="https://example.com/doc.pdf",
            document_id="doc_1",
        )
    """

    def __init__(self, *, config: MineruApiConfig, name: str = "mineru", version: str = "v1") -> None:
        self.name = name
        self.version = version
        self._client = MineruOfficialApiClient(config)
        self._config = config

    def parse_from_url(
        self,
        *,
        file_url: str,
        document_id: str,
        page_ranges: str | None = None,
        parser_version: str | None = None,
    ) -> dict[str, object]:
        """Parse PDF from URL using MinerU Official API.

        This is the main entry point for the adapter.
        """
        # Step 1: Submit task
        task_id = self._client.submit_task(
            file_url=file_url,
            page_ranges=page_ranges,
        )

        # Step 2: Poll until complete
        zip_url = self._client.poll_until_complete(task_id=task_id)

        # Step 3: Download and extract
        content = self._client.download_and_extract_zip(zip_url=zip_url)

        # Step 4: Parse content_list.json (SSOT §2.3 priority 1)
        content_list = self._extract_content_list(content)
        full_md = self._extract_full_md(content)

        # Step 5: Build chunk from content_list
        if content_list:
            # Take first meaningful item
            for item in content_list:
                if item.text.strip():
                    heading_path = self._build_heading_path(item, full_md)
                    return item.to_chunk_dict(
                        document_id=document_id,
                        parser=self.name,
                        parser_version=parser_version or self.version,
                        section="mineru_official_parsed",
                        heading_path=heading_path,
                    )

        # Fallback: use full.md if no content_list
        if full_md:
            return {
                "document_id": document_id,
                "pages": [1],
                "positions": [{"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0], "start": 0, "end": len(full_md)}],
                "section": "mineru_official_parsed",
                "heading_path": ["content"],
                "chunk_type": "text",
                "parser": self.name,
                "parser_version": parser_version or self.version,
                "content_source": "mineru_full_md",
                "text": full_md[:5000],  # Truncate for chunk
            }

        raise ApiError(
            code="DOC_PARSE_OUTPUT_NOT_FOUND",
            message="MinerU result contains no parseable content",
            error_class="transient",
            retryable=True,
            http_status=503,
        )

    def _extract_content_list(self, content: dict[str, str]) -> list[MineruContentItem]:
        """Extract content_list from zip content (SSOT §2.3)."""
        # Priority 1: *_content_list.json
        for name, text in content.items():
            if name.endswith("_content_list.json"):
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        return [MineruContentItem.from_dict(item) for item in data]
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

        # Priority 2: *context_list.json (legacy naming)
        for name, text in content.items():
            if name.endswith("context_list.json"):
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        return [MineruContentItem.from_dict(item) for item in data]
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

        return []

    def _extract_full_md(self, content: dict[str, str]) -> str | None:
        """Extract full.md from zip content (SSOT §2.3)."""
        # Priority 3: full.md
        for name, text in content.items():
            if name == "full.md" or name.endswith("/full.md"):
                return text

        # Priority 4: *.md
        for name, text in content.items():
            if name.endswith(".md"):
                return text

        return None

    def _build_heading_path(
        self,
        item: MineruContentItem,
        full_md: str | None,
    ) -> list[str]:
        """Build heading_path from text_level and markdown structure."""
        if item.text_level is not None and item.text_level >= 1:
            # Use text_level to indicate heading
            return [f"h{item.text_level}", item.text[:50]]

        return ["content"]
