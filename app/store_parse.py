from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from typing import Any

from app.errors import ApiError
from app.parser_adapters import ParseRoute, select_parse_route


class StoreParseMixin:
    """Parse document files with support for MinerU Official API.

    SSOT Alignment:
    - §3 解析器路由: mineru -> docling -> ocr
    - §4 parse manifest 契约
    - §8 持久化顺序: raw_file → parse manifest → chunks
    """

    def _try_mineru_official_api(
        self,
        *,
        document: dict[str, Any],
        document_id: str,
        tenant_id: str,
        job_id: str,
        trace_id: str | None,
    ) -> list[dict[str, Any]] | None:
        """Try parsing with MinerU Official API if configured.

        Supports two scenarios:
        1. Document has source_url (public URL to file) → use directly
        2. Document has storage_uri → generate presigned URL (S3 only)

        Requires:
        1. MINERU_API_KEY environment variable
        2. Document has source_url OR storage_uri (with S3 backend)

        Returns:
        - List of chunks if successful
        - None if MinerU Official API not available or no accessible URL
        """
        # Check if MinerU Official API is configured
        api_key = os.environ.get("MINERU_API_KEY", "")
        if not api_key.strip():
            return None

        # Determine the file URL
        file_url: str | None = None

        # Option 1: Use source_url if available
        source_url = document.get("source_url")
        if source_url and isinstance(source_url, str) and source_url.strip():
            file_url = source_url.strip()

        # Option 2: Generate presigned URL from storage_uri
        if not file_url:
            storage_uri = document.get("storage_uri")
            if storage_uri and isinstance(storage_uri, str) and storage_uri.strip():
                # Try to generate presigned URL (S3 backend supports this)
                presigned = self.object_storage.get_presigned_url(
                    storage_uri=storage_uri,
                    expires_in=3600,  # 1 hour
                )
                if presigned:
                    file_url = presigned

        # No accessible URL found
        if not file_url:
            return None

        # Try to use MinerU Official API
        try:
            from app.mineru_parse_service import build_mineru_parse_service

            service = build_mineru_parse_service(
                object_storage=self.object_storage,
                parse_manifests_repo=self.parse_manifests_repository,
                documents_repo=self.documents_repository,
            )

            if service is None:
                return None

            # Get existing manifest for job info
            manifest = self.parse_manifests_repository.get(tenant_id=tenant_id, job_id=job_id)

            result = service.parse_and_persist(
                file_url=file_url,
                document_id=document_id,
                tenant_id=tenant_id,
                job_id=job_id,
                selected_parser=manifest.get("selected_parser", "mineru_official") if manifest else "mineru_official",
                parser_version=manifest.get("parser_version", "v1") if manifest else "v1",
                fallback_chain=manifest.get("fallback_chain", []) if manifest else [],
                trace_id=trace_id,
            )

            # Get persisted chunks
            chunks = self.documents_repository.get_chunks(
                tenant_id=tenant_id,
                document_id=document_id,
            )

            return [self._ensure_chunk_shape(document_id=document_id, chunk=c) for c in chunks]

        except Exception:
            # MinerU Official API failed, return None to fall back to local parsing
            return None
    @staticmethod
    def _select_parser(*, filename: str, doc_type: str | None) -> ParseRoute:
        return select_parse_route(filename=filename, doc_type=doc_type)

    @staticmethod
    def _classify_error_code(error_code: str) -> dict[str, Any]:
        matrix: dict[str, dict[str, Any]] = {
            "DOC_PARSE_OUTPUT_NOT_FOUND": {
                "class": "permanent",
                "retryable": False,
                "message": "parse output missing",
            },
            "DOC_PARSE_SCHEMA_INVALID": {
                "class": "transient",
                "retryable": True,
                "message": "parse schema invalid",
            },
            "MINERU_BBOX_FORMAT_INVALID": {
                "class": "permanent",
                "retryable": False,
                "message": "bbox format invalid",
            },
            "TEXT_ENCODING_UNSUPPORTED": {
                "class": "permanent",
                "retryable": False,
                "message": "text encoding unsupported",
            },
            "PARSER_FALLBACK_EXHAUSTED": {
                "class": "transient",
                "retryable": True,
                "message": "parser fallback exhausted",
            },
            "RAG_UPSTREAM_UNAVAILABLE": {
                "class": "transient",
                "retryable": True,
                "message": "retrieval upstream unavailable",
            },
            "INTERNAL_DEBUG_FORCED_FAIL": {
                "class": "transient",
                "retryable": True,
                "message": "forced failure by internal debug run",
            },
        }
        return matrix.get(
            error_code,
            {
                "class": "transient",
                "retryable": True,
                "message": "forced failure by internal debug run",
            },
        )

    @staticmethod
    def _normalize_and_rewrite_query(query: str, include_terms: list[str], exclude_terms: list[str]) -> dict[str, Any]:
        from app.constraint_extractor import extract_constraints

        normalized = re.sub(r"\s+", " ", query).strip()
        rewritten = normalized
        parts: list[str] = []
        if include_terms:
            parts.append("include:" + ",".join(include_terms))
        if exclude_terms:
            parts.append("exclude:" + ",".join(exclude_terms))
        if parts:
            rewritten = f"{normalized} [{' | '.join(parts)}]"
        diff: list[str] = []
        lower_rewritten = rewritten.lower()
        for term in include_terms:
            if term not in lower_rewritten:
                diff.append(f"missing_include:{term}")
        for term in exclude_terms:
            if term not in lower_rewritten:
                diff.append(f"missing_exclude:{term}")

        constraints = extract_constraints(normalized)

        return {
            "rewritten_query": rewritten,
            "rewrite_reason": "normalize_whitespace_and_constraints",
            "constraints_preserved": len(diff) == 0,
            "constraint_diff": diff,
            "entity_constraints": constraints["entity_constraints"],
            "numeric_constraints": constraints["numeric_constraints"],
            "time_constraints": constraints["time_constraints"],
        }

    @staticmethod
    def _extract_page_and_bbox(chunk: dict[str, Any]) -> tuple[int, list[float]]:
        positions = chunk.get("positions", [])
        if isinstance(positions, list) and positions:
            first = positions[0] if isinstance(positions[0], dict) else {}
            page = int(first.get("page") or 1)
            bbox = first.get("bbox")
            if isinstance(bbox, list) and len(bbox) == 4:
                try:
                    return page, [float(x) for x in bbox]
                except (TypeError, ValueError):
                    return page, [0.0, 0.0, 1.0, 1.0]
        page = int(chunk.get("page") or 1)
        bbox = chunk.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            try:
                return page, [float(x) for x in bbox]
            except (TypeError, ValueError):
                return page, [0.0, 0.0, 1.0, 1.0]
        return page, [0.0, 0.0, 1.0, 1.0]

    @classmethod
    def _ensure_chunk_shape(cls, *, document_id: str, chunk: dict[str, Any]) -> dict[str, Any]:
        item = dict(chunk)
        page, bbox = cls._extract_page_and_bbox(item)
        text = str(item.get("text") or "")
        heading_path = item.get("heading_path")
        if not isinstance(heading_path, list):
            heading_path = []
        hash_key = json.dumps(
            {
                "document_id": document_id,
                "page": page,
                "bbox": bbox,
                "heading_path": heading_path,
                "text": text,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        chunk_hash = hashlib.sha256(hash_key.encode("utf-8")).hexdigest()
        item["document_id"] = document_id
        item["page"] = page
        item["bbox"] = bbox
        item["chunk_hash"] = chunk_hash
        if not item.get("chunk_id"):
            item["chunk_id"] = f"ck_{chunk_hash[:12]}"
        if "positions" not in item or not isinstance(item.get("positions"), list) or not item["positions"]:
            item["positions"] = [{"page": page, "bbox": bbox, "start": 0, "end": max(1, len(text))}]
        if "pages" not in item or not isinstance(item.get("pages"), list) or not item["pages"]:
            item["pages"] = [page]
        if "heading_path" not in item or not isinstance(item.get("heading_path"), list):
            item["heading_path"] = []
        item.setdefault("chunk_type", "text")
        item.setdefault("parser", "mineru")
        item.setdefault("parser_version", "v0")
        item.setdefault("section", "")
        item.setdefault("content_source", "unknown")
        item.setdefault("text", text)
        return item

    def _parse_document_file(
        self,
        *,
        document: dict[str, Any],
        document_id: str,
        tenant_id: str,
        manifest: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Parse document file with SSOT §3 routing priority.

        Priority:
        1. MinerU Official API (if MINERU_API_KEY + (source_url or presigned URL))
        2. Local parser (PyMuPDF/python-docx)
        3. Stub adapter (fallback)
        """
        filename = str(document.get("filename") or "upload.bin")
        job_id = manifest.get("job_id") if manifest else None
        trace_id = manifest.get("trace_id") if manifest else None

        # Priority 1: Try MinerU Official API (SSOT §3.1)
        if job_id:
            mineru_chunks = self._try_mineru_official_api(
                document=document,
                document_id=document_id,
                tenant_id=tenant_id,
                job_id=job_id,
                trace_id=trace_id,
            )
            if mineru_chunks:
                self.parser_retrieval_metrics["parse_mineru_official_used_total"] += 1
                return mineru_chunks

        # Priority 2: Try local parser (PyMuPDF/python-docx)
        storage_uri = document.get("storage_uri")
        file_bytes: bytes | None = None

        if storage_uri:
            try:
                file_bytes = self.object_storage.get_object(storage_uri=storage_uri)
            except Exception:
                file_bytes = None

        if file_bytes and len(file_bytes) > 0:
            local_adapter = self._parser_registry._adapters.get("local")
            if local_adapter is not None and hasattr(local_adapter, "parse_file"):
                try:
                    raw_chunks = local_adapter.parse_file(
                        file_bytes=file_bytes,
                        filename=filename,
                        document_id=document_id,
                    )
                    if raw_chunks:
                        return [self._ensure_chunk_shape(document_id=document_id, chunk=c) for c in raw_chunks]
                except Exception:
                    pass

        # Priority 3: Stub adapter (fallback)
        selected_parser = manifest["selected_parser"] if manifest else "mineru"
        parser_version = manifest.get("parser_version", "v0") if manifest else "v0"
        fallback_chain = list(manifest.get("fallback_chain", [])) if manifest else []
        route = ParseRoute(
            selected_parser=selected_parser,
            fallback_chain=fallback_chain,
            parser_version=parser_version,
        )
        chunk = self._parser_registry.parse_with_route(
            route=route,
            document_id=document_id,
            default_text="chunk generated by parse skeleton",
        )
        normalized_chunk = self._ensure_chunk_shape(document_id=document_id, chunk=chunk)
        if normalized_chunk.get("parser") != route.selected_parser:
            self.parser_retrieval_metrics["parse_fallback_used_total"] += 1
        return [normalized_chunk]

    def _dedupe_chunks(
        self,
        *,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for chunk in chunks:
            normalized = self._ensure_chunk_shape(document_id=document_id, chunk=chunk)
            key = str(normalized.get("chunk_hash", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(normalized)
        return out

    def create_parse_job(self, *, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        document = self.get_document_for_tenant(
            document_id=document_id, tenant_id=payload.get("tenant_id", "tenant_default")
        )
        if document is None:
            raise ApiError(
                code="DOC_NOT_FOUND",
                message="document not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )
        tenant_id = payload.get("tenant_id", "tenant_default")
        self._assert_tenant_scope(document["tenant_id"], tenant_id)
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        thread_id = self._new_thread_id("parse")
        self._persist_job(
            job={
                "job_id": job_id,
                "job_type": "parse",
                "status": "queued",
                "retry_count": 0,
                "thread_id": thread_id,
                "tenant_id": tenant_id,
                "trace_id": payload.get("trace_id"),
                "resource": {
                    "type": "document",
                    "id": document_id,
                },
                "payload": payload,
                "last_error": None,
                "errors": [],  # SSOT: errors array
            }
        )
        route = self._select_parser(
            filename=document.get("filename", ""),
            doc_type=document.get("doc_type"),
        )
        self._persist_parse_manifest(
            manifest={
                "run_id": f"prun_{uuid.uuid4().hex[:12]}",
                "job_id": job_id,
                "document_id": document_id,
                "tenant_id": tenant_id,
                "selected_parser": route.selected_parser,
                "parser_version": route.parser_version,
                "fallback_chain": route.fallback_chain,
                "input_files": [
                    {
                        "name": document.get("filename"),
                        "sha256": document.get("file_sha256"),
                        "size": int(document.get("file_size") or 0),
                    }
                ],
                "started_at": None,
                "ended_at": None,
                "status": "queued",
                "error_code": None,
            }
        )
        document["status"] = "parse_queued"
        self._persist_document(document=document)
        self.append_outbox_event(
            tenant_id=tenant_id,
            event_type="job.created",
            aggregate_type="job",
            aggregate_id=job_id,
            payload={
                "job_id": job_id,
                "job_type": "parse",
                "resource_type": "document",
                "resource_id": document_id,
            },
        )
        return {
            "document_id": document_id,
            "job_id": job_id,
            "status": "queued",
        }

    def get_parse_manifest_for_tenant(self, *, job_id: str, tenant_id: str) -> dict[str, Any] | None:
        manifest = self.parse_manifests_repository.get(tenant_id=tenant_id, job_id=job_id)
        if manifest is None:
            return None
        return manifest
