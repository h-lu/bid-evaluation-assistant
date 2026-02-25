"""MinerU Parse Service with Persistence.

Handles the full parse flow including:
1. Submit document to MinerU API
2. Download and save result zip to object storage
3. Parse content_list.json into chunks
4. Persist chunks to database
5. Update parse manifest

SSOT Alignment:
- §4 parse manifest 契约
- §8 持久化顺序: raw_file → parse manifest → chunks → vectors
- §7.3 chunk 元数据最小字段
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.errors import ApiError
from app.mineru_official_api import (
    MineruApiConfig,
    MineruContentItem,
    MineruOfficialApiClient,
)


class ObjectStorageBackend(Protocol):
    """Protocol for object storage operations."""

    def put_object(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str | None = None,
    ) -> str: ...

    def get_object(self, *, storage_uri: str) -> bytes: ...


class ParseManifestRepository(Protocol):
    """Protocol for parse manifest repository."""

    def upsert(self, *, tenant_id: str, manifest: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, *, tenant_id: str, job_id: str) -> dict[str, Any] | None: ...


class DocumentRepository(Protocol):
    """Protocol for document repository."""

    def upsert_document(self, *, document: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, *, tenant_id: str, document_id: str) -> dict[str, Any] | None: ...

    def replace_chunks(
        self,
        *,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...


@dataclass
class MineruParseResult:
    """Result of MinerU parse with persistence."""
    document_id: str
    job_id: str
    status: str
    chunks_count: int
    zip_storage_uri: str | None
    images_storage_uris: list[str] | None  # URIs for extracted images
    images_count: int  # Number of images extracted
    content_list: list[dict[str, Any]]
    full_md: str | None
    parse_time_s: float


class MineruParseService:
    """Service for parsing documents with MinerU and persisting results.

    Usage:
        service = MineruParseService(
            config=config,
            object_storage=storage,
            parse_manifests_repo=repo,
            documents_repo=doc_repo,
        )

        result = await service.parse_and_persist(
            file_url="https://example.com/doc.pdf",
            document_id="doc_123",
            tenant_id="tenant_abc",
            job_id="job_xyz",
        )
    """

    def __init__(
        self,
        *,
        config: MineruApiConfig,
        object_storage: ObjectStorageBackend,
        parse_manifests_repo: ParseManifestRepository,
        documents_repo: DocumentRepository,
    ) -> None:
        self._config = config
        self._client = MineruOfficialApiClient(config)
        self._object_storage = object_storage
        self._parse_manifests_repo = parse_manifests_repo
        self._documents_repo = documents_repo

    def parse_and_persist(
        self,
        *,
        file_url: str,
        document_id: str,
        tenant_id: str,
        job_id: str,
        selected_parser: str = "mineru_official",
        parser_version: str = "v1",
        fallback_chain: list[str] | None = None,
        trace_id: str | None = None,
    ) -> MineruParseResult:
        """Parse document with MinerU and persist all results.

        SSOT §8 持久化顺序:
        1. raw_file stored (already done before this)
        2. parse manifest stored (created in create_parse_job)
        3. chunks stored (this method)
        4. vectors indexed (done separately)
        """
        start_time = time.time()

        # Get existing manifest
        manifest = self._parse_manifests_repo.get(tenant_id=tenant_id, job_id=job_id)
        if manifest is None:
            manifest = {
                "job_id": job_id,
                "document_id": document_id,
                "tenant_id": tenant_id,
                "selected_parser": selected_parser,
                "parser_version": parser_version,
                "fallback_chain": fallback_chain or [],
                "input_files": [],
                "started_at": datetime.now(tz=UTC).isoformat(),
                "status": "parsing",
                "error_code": None,
            }

        # Update manifest: start parsing
        manifest["status"] = "parsing"
        manifest["started_at"] = datetime.now(tz=UTC).isoformat()
        self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)

        try:
            # Step 1: Submit task to MinerU
            task_id = self._client.submit_task(file_url=file_url)

            # Step 2: Poll until complete
            zip_url = self._client.poll_until_complete(task_id=task_id)

            # Step 3: Download zip
            zip_bytes = self._download_zip(zip_url)

            # Step 4: Save zip to object storage
            zip_storage_uri = self._save_parse_result(
                tenant_id=tenant_id,
                document_id=document_id,
                zip_bytes=zip_bytes,
            )

            # Step 5: Extract content from zip
            content = self._extract_zip_content(zip_bytes)
            content_list = self._parse_content_list(content)
            full_md = self._extract_full_md(content)

            # Step 5.5: Extract and save images from zip
            images_storage_uris = self._save_images(
                tenant_id=tenant_id,
                document_id=document_id,
                zip_bytes=zip_bytes,
            )

            # Step 6: Convert content_list to chunks
            chunks = self._content_list_to_chunks(
                content_list=content_list,
                document_id=document_id,
                tenant_id=tenant_id,
                parser=selected_parser,
                parser_version=parser_version,
                full_md=full_md,
            )

            # Step 7: Persist chunks
            if chunks:
                self._documents_repo.replace_chunks(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    chunks=chunks,
                )

            # Step 8: Update manifest: success
            manifest["status"] = "completed"
            manifest["ended_at"] = datetime.now(tz=UTC).isoformat()
            manifest["error_code"] = None
            manifest["images_count"] = len(images_storage_uris)
            self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)

            # Step 9: Update document status
            document = self._documents_repo.get(tenant_id=tenant_id, document_id=document_id)
            if document:
                document["status"] = "parsed"
                document["parse_result_uri"] = zip_storage_uri
                self._documents_repo.upsert_document(document=document)

            parse_time = time.time() - start_time

            return MineruParseResult(
                document_id=document_id,
                job_id=job_id,
                status="completed",
                chunks_count=len(chunks),
                zip_storage_uri=zip_storage_uri,
                images_storage_uris=images_storage_uris,
                images_count=len(images_storage_uris),
                content_list=[self._item_to_dict(item) for item in content_list],
                full_md=full_md,
                parse_time_s=parse_time,
            )

        except ApiError as e:
            # Update manifest: failed
            manifest["status"] = "failed"
            manifest["ended_at"] = datetime.now(tz=UTC).isoformat()
            manifest["error_code"] = e.code
            self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)
            raise

        except Exception as e:
            # Update manifest: failed with unknown error
            manifest["status"] = "failed"
            manifest["ended_at"] = datetime.now(tz=UTC).isoformat()
            manifest["error_code"] = "DOC_PARSE_UNKNOWN_ERROR"
            self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)
            raise ApiError(
                code="DOC_PARSE_UNKNOWN_ERROR",
                message=f"MinerU parse failed: {e}",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from e

    def parse_and_persist_from_bytes(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        document_id: str,
        tenant_id: str,
        job_id: str,
        selected_parser: str = "mineru_official",
        parser_version: str = "v1",
        fallback_chain: list[str] | None = None,
        trace_id: str | None = None,
    ) -> MineruParseResult:
        """Parse document from raw bytes using MinerU file upload API.

        This method uses MinerU's /file-urls/batch API for direct file upload,
        which is simpler than the URL-based approach.

        Workflow:
        1. Request upload URL from MinerU
        2. Upload file bytes to the pre-signed URL
        3. Poll for batch completion
        4. Download and parse result
        5. Persist chunks to database

        Args:
            file_bytes: Raw PDF file content
            filename: Original filename
            document_id: Unique document identifier
            tenant_id: Tenant identifier
            job_id: Parse job identifier
            selected_parser: Parser name (default: "mineru_official")
            parser_version: Parser version string
            fallback_chain: List of fallback parsers
            trace_id: Trace ID for logging

        Returns:
            MineruParseResult with parse status and chunk count
        """
        start_time = time.time()

        # Get existing manifest
        manifest = self._parse_manifests_repo.get(tenant_id=tenant_id, job_id=job_id)
        if manifest is None:
            manifest = {
                "job_id": job_id,
                "document_id": document_id,
                "tenant_id": tenant_id,
                "selected_parser": selected_parser,
                "parser_version": parser_version,
                "fallback_chain": fallback_chain or [],
                "input_files": [{"name": filename, "size": len(file_bytes)}],
                "started_at": datetime.now(tz=UTC).isoformat(),
                "status": "parsing",
                "error_code": None,
            }

        # Update manifest: start parsing
        manifest["status"] = "parsing"
        manifest["started_at"] = datetime.now(tz=UTC).isoformat()
        self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)

        try:
            # Step 1: Request upload URL
            data_id = document_id or "doc"
            batch_id, upload_urls = self._client.request_upload_urls(
                files=[{"name": filename, "data_id": data_id}],
            )

            if not upload_urls:
                raise ApiError(
                    code="DOC_PARSE_UPSTREAM_ERROR",
                    message="MinerU did not return upload URL",
                    error_class="transient",
                    retryable=True,
                    http_status=503,
                )

            # Step 2: Upload file
            self._client.upload_file_to_url(
                file_bytes=file_bytes,
                upload_url=upload_urls[0],
            )

            # Step 3: Poll until complete
            zip_urls = self._client.poll_batch_until_complete(batch_id=batch_id)

            # Step 4: Download zip
            zip_bytes = self._download_zip(zip_urls[0])

            # Step 5: Save zip to object storage
            zip_storage_uri = self._save_parse_result(
                tenant_id=tenant_id,
                document_id=document_id,
                zip_bytes=zip_bytes,
            )

            # Step 6: Extract content from zip
            content = self._extract_zip_content(zip_bytes)
            content_list = self._parse_content_list(content)
            full_md = self._extract_full_md(content)

            # Step 6.5: Extract and save images from zip
            images_storage_uris = self._save_images(
                tenant_id=tenant_id,
                document_id=document_id,
                zip_bytes=zip_bytes,
            )

            # Step 7: Convert content_list to chunks
            chunks = self._content_list_to_chunks(
                content_list=content_list,
                document_id=document_id,
                tenant_id=tenant_id,
                parser=selected_parser,
                parser_version=parser_version,
                full_md=full_md,
            )

            # Step 8: Persist chunks
            if chunks:
                self._documents_repo.replace_chunks(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    chunks=chunks,
                )

            # Step 9: Update manifest: success
            manifest["status"] = "completed"
            manifest["ended_at"] = datetime.now(tz=UTC).isoformat()
            manifest["error_code"] = None
            manifest["images_count"] = len(images_storage_uris)
            self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)

            # Step 10: Update document status
            document = self._documents_repo.get(tenant_id=tenant_id, document_id=document_id)
            if document:
                document["status"] = "parsed"
                document["parse_result_uri"] = zip_storage_uri
                self._documents_repo.upsert_document(document=document)

            parse_time = time.time() - start_time

            return MineruParseResult(
                document_id=document_id,
                job_id=job_id,
                status="completed",
                chunks_count=len(chunks),
                zip_storage_uri=zip_storage_uri,
                images_storage_uris=images_storage_uris,
                images_count=len(images_storage_uris),
                content_list=[self._item_to_dict(item) for item in content_list],
                full_md=full_md,
                parse_time_s=parse_time,
            )

        except ApiError as e:
            # Update manifest: failed
            manifest["status"] = "failed"
            manifest["ended_at"] = datetime.now(tz=UTC).isoformat()
            manifest["error_code"] = e.code
            self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)
            raise

        except Exception as e:
            # Update manifest: failed with unknown error
            manifest["status"] = "failed"
            manifest["ended_at"] = datetime.now(tz=UTC).isoformat()
            manifest["error_code"] = "DOC_PARSE_UNKNOWN_ERROR"
            self._parse_manifests_repo.upsert(tenant_id=tenant_id, manifest=manifest)
            raise ApiError(
                code="DOC_PARSE_UNKNOWN_ERROR",
                message=f"MinerU parse failed: {e}",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from e

    def _download_zip(self, zip_url: str) -> bytes:
        """Download zip file from URL."""
        from urllib import request

        try:
            with request.urlopen(zip_url, timeout=60) as resp:
                return resp.read()
        except Exception as e:
            raise ApiError(
                code="DOC_PARSE_OUTPUT_NOT_FOUND",
                message=f"Failed to download MinerU result: {e}",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from e

    def _save_parse_result(
        self,
        *,
        tenant_id: str,
        document_id: str,
        zip_bytes: bytes,
    ) -> str:
        """Save parse result zip to object storage.

        Key format per SSOT: tenants/{tenant_id}/documents/{document_id}/parse/result.zip
        """
        return self._object_storage.put_object(
            tenant_id=tenant_id,
            object_type="document_parse",
            object_id=document_id,
            filename="result.zip",
            content_bytes=zip_bytes,
            content_type="application/zip",
        )

    def _extract_zip_content(self, zip_bytes: bytes) -> dict[str, str]:
        """Extract text content from zip."""
        content: dict[str, str] = {}
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
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

    def _save_images(
        self,
        *,
        tenant_id: str,
        document_id: str,
        zip_bytes: bytes,
    ) -> list[str]:
        """Extract and save images from zip to object storage.

        Images are stored at: tenants/{tenant_id}/document_parse/{document_id}/images/{filename}

        Returns list of storage URIs for saved images.
        """
        storage_uris: list[str] = []
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg"}

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    # Check if file is in images directory and has image extension
                    lower_name = name.lower()
                    if name.startswith("images/") or "/images/" in name:
                        ext = os.path.splitext(name)[1].lower()
                        if ext in image_extensions:
                            # Extract filename from path
                            filename = os.path.basename(name)
                            if not filename:
                                continue

                            # Read image bytes
                            image_bytes = zf.read(name)
                            if len(image_bytes) == 0:
                                continue

                            # Determine content type
                            content_type_map = {
                                ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg",
                                ".png": "image/png",
                                ".gif": "image/gif",
                                ".webp": "image/webp",
                                ".bmp": "image/bmp",
                                ".tiff": "image/tiff",
                                ".svg": "image/svg+xml",
                            }
                            content_type = content_type_map.get(ext, "application/octet-stream")

                            # Save to object storage
                            uri = self._object_storage.put_object(
                                tenant_id=tenant_id,
                                object_type="document_parse",
                                object_id=f"{document_id}/images",
                                filename=filename,
                                content_bytes=image_bytes,
                                content_type=content_type,
                            )
                            storage_uris.append(uri)

        except zipfile.BadZipFile:
            # Log warning but don't fail - images are optional
            pass

        return storage_uris

    def _parse_content_list(self, content: dict[str, str]) -> list[MineruContentItem]:
        """Parse content_list.json following SSOT §2.3 priority."""
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
        """Extract full.md following SSOT §2.3 priority."""
        # Priority 3: full.md
        for name, text in content.items():
            if name == "full.md" or name.endswith("/full.md"):
                return text

        # Priority 4: *.md
        for name, text in content.items():
            if name.endswith(".md"):
                return text

        return None

    def _content_list_to_chunks(
        self,
        *,
        content_list: list[MineruContentItem],
        document_id: str,
        tenant_id: str,
        parser: str,
        parser_version: str,
        full_md: str | None,
    ) -> list[dict[str, Any]]:
        """Convert content_list to chunks per SSOT §7.3.

        Chunk fields:
        - chunk_id
        - tenant_id
        - document_id
        - pages[]
        - positions[] (page, bbox, start, end)
        - section
        - heading_path[]
        - chunk_type
        - parser
        - parser_version
        - text
        - img_path (for image chunks)
        - image_caption (for image chunks)
        """
        chunks: list[dict[str, Any]] = []

        for idx, item in enumerate(content_list):
            # Skip items without text unless they are images with img_path
            if not item.text.strip() and item.type != "image" and not item.img_path:
                continue

            # For image items, use caption as text if available
            text = item.text
            if not text.strip() and item.image_caption:
                text = " ".join(item.image_caption)
            if not text.strip() and item.img_path:
                text = f"[Image: {os.path.basename(item.img_path)}]"

            # Generate chunk_id from hash
            chunk_hash = self._compute_chunk_hash(
                document_id=document_id,
                page_idx=item.page_idx,
                bbox=item.bbox,
                text=text,
            )

            # Build heading_path from text_level
            heading_path = self._build_heading_path(item, full_md)

            chunk = {
                "chunk_id": f"ck_{chunk_hash[:12]}",
                "chunk_hash": chunk_hash,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "pages": [item.page_idx + 1],  # Convert 0-indexed to 1-indexed
                "positions": [
                    {
                        "page": item.page_idx + 1,
                        "bbox": item.bbox,
                        "start": 0,
                        "end": len(text),
                    }
                ],
                "section": self._infer_section(item, full_md),
                "heading_path": heading_path,
                "chunk_type": item.type,
                "parser": parser,
                "parser_version": parser_version,
                "content_source": "mineru_official_api",
                "text": text,
            }

            # Add image-related fields if present
            if item.img_path:
                chunk["img_path"] = item.img_path
            if item.image_caption:
                chunk["image_caption"] = item.image_caption

            chunks.append(chunk)

        return chunks

    def _compute_chunk_hash(
        self,
        *,
        document_id: str,
        page_idx: int,
        bbox: list[float],
        text: str,
    ) -> str:
        """Compute deterministic hash for chunk."""
        hash_key = json.dumps(
            {
                "document_id": document_id,
                "page_idx": page_idx,
                "bbox": bbox,
                "text": text,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(hash_key.encode("utf-8")).hexdigest()

    def _build_heading_path(
        self,
        item: MineruContentItem,
        full_md: str | None,
    ) -> list[str]:
        """Build heading_path from text_level and markdown structure."""
        if item.text_level is not None and item.text_level >= 1:
            return [f"h{item.text_level}", item.text[:50].strip()]
        return ["content"]

    def _infer_section(
        self,
        item: MineruContentItem,
        full_md: str | None,
    ) -> str:
        """Infer section from item type and content."""
        if item.text_level is not None:
            level_names = {1: "title", 2: "section", 3: "subsection", 4: "subsubsection"}
            return level_names.get(item.text_level, "content")
        return "content"

    def _item_to_dict(self, item: MineruContentItem) -> dict[str, Any]:
        """Convert MineruContentItem to dict."""
        result = {
            "text": item.text,
            "type": item.type,
            "page_idx": item.page_idx,
            "bbox": item.bbox,
            "text_level": item.text_level,
        }
        if item.img_path:
            result["img_path"] = item.img_path
        if item.image_caption:
            result["image_caption"] = item.image_caption
        return result


def build_mineru_parse_service(
    *,
    object_storage: ObjectStorageBackend,
    parse_manifests_repo: ParseManifestRepository,
    documents_repo: DocumentRepository,
    env: dict[str, str] | None = None,
) -> MineruParseService | None:
    """Build MineruParseService if MINERU_API_KEY is configured."""
    import os

    source = os.environ if env is None else env
    api_key = source.get("MINERU_API_KEY", "")

    if not api_key.strip():
        return None

    config = MineruApiConfig(
        api_key=api_key,
        timeout_s=float(source.get("MINERU_TIMEOUT_S", "30") or "30"),
        max_poll_time_s=float(source.get("MINERU_MAX_POLL_TIME_S", "180") or "180"),
        is_ocr=source.get("MINERU_IS_OCR", "true").strip().lower() not in {"0", "false", "no", "off"},
        enable_formula=source.get("MINERU_ENABLE_FORMULA", "false").strip().lower() in {"1", "true", "yes", "on"},
    )

    return MineruParseService(
        config=config,
        object_storage=object_storage,
        parse_manifests_repo=parse_manifests_repo,
        documents_repo=documents_repo,
    )
