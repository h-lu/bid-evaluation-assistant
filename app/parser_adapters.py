from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib import request
from urllib.error import URLError

from app.errors import ApiError
from app.parse_utils import normalize_bbox


@dataclass(frozen=True)
class ParseRoute:
    selected_parser: str
    fallback_chain: list[str]
    parser_version: str = "v0"


class ParserAdapter(Protocol):
    name: str
    version: str

    def parse(self, *, document_id: str, default_text: str, parser_version: str) -> dict[str, object]: ...


class StubParserAdapter:
    def __init__(self, *, name: str, version: str = "v0", section: str) -> None:
        self.name = name
        self.version = version
        self._section = section

    def parse(self, *, document_id: str, default_text: str, parser_version: str) -> dict[str, object]:
        return {
            "document_id": document_id,
            "pages": [1],
            "positions": [
                {
                    "page": 1,
                    "bbox": normalize_bbox([100, 120, 520, 380]),
                    "start": 0,
                    "end": 128,
                }
            ],
            "section": self._section,
            "heading_path": ["section-1", self.name],
            "chunk_type": "text",
            "parser": self.name,
            "parser_version": parser_version or self.version,
            "content_source": "stub",
            "text": default_text,
        }


def _post_json(*, endpoint: str, payload: dict[str, object], timeout_s: float) -> object:
    body = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


class HttpParserAdapter(StubParserAdapter):
    """Use external parser endpoint when configured; fallback to stub behavior otherwise."""

    def __init__(
        self,
        *,
        name: str,
        section: str,
        endpoint: str,
        timeout_s: float,
        version: str = "v0",
    ) -> None:
        super().__init__(name=name, section=section, version=version)
        self._endpoint = endpoint.strip()
        self._timeout_s = timeout_s

    @staticmethod
    def _normalized_chunk(
        *,
        source: Mapping[str, object],
        parser: str,
        parser_version: str,
        document_id: str,
        default_text: str,
        default_section: str,
        content_source: str,
    ) -> dict[str, object]:
        text = str(source.get("text") or default_text)
        page = int(source.get("page") or 1)
        bbox = source.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [100, 120, 520, 380]
        bbox = normalize_bbox(bbox)
        heading_path = source.get("heading_path")
        if not isinstance(heading_path, list) or not heading_path:
            heading_path = ["section-1", parser]
        return {
            "document_id": document_id,
            "pages": [page],
            "positions": [
                {
                    "page": page,
                    "bbox": bbox,
                    "start": 0,
                    "end": max(1, len(text)),
                }
            ],
            "section": str(source.get("section") or default_section),
            "heading_path": heading_path,
            "chunk_type": str(source.get("chunk_type") or "text"),
            "parser": parser,
            "parser_version": parser_version,
            "content_source": content_source,
            "text": text,
        }

    def _chunk_from_response(
        self,
        *,
        payload: Mapping[str, object],
        document_id: str,
        parser_version: str,
        default_text: str,
    ) -> dict[str, object]:
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            for row in chunks:
                if isinstance(row, Mapping):
                    return self._normalized_chunk(
                        source=row,
                        parser=self.name,
                        parser_version=parser_version,
                        document_id=document_id,
                        default_text=default_text,
                        default_section=f"{self.name}_parsed",
                        content_source="chunks",
                    )

        content_list = payload.get("content_list")
        if isinstance(content_list, list):
            for row in content_list:
                if isinstance(row, Mapping):
                    return self._normalized_chunk(
                        source=row,
                        parser=self.name,
                        parser_version=parser_version,
                        document_id=document_id,
                        default_text=default_text,
                        default_section=f"{self.name}_parsed",
                        content_source="content_list",
                    )

        full_md = payload.get("full_md")
        if not isinstance(full_md, str):
            candidate = payload.get("full.md")
            full_md = candidate if isinstance(candidate, str) else None
        if isinstance(full_md, str) and full_md.strip():
            return self._normalized_chunk(
                source={"text": full_md.strip(), "page": 1},
                parser=self.name,
                parser_version=parser_version,
                document_id=document_id,
                default_text=default_text,
                default_section=f"{self.name}_parsed",
                content_source="full_md",
            )

        raise ApiError(
            code="DOC_PARSE_OUTPUT_NOT_FOUND",
            message=f"{self.name} response does not contain parse payload",
            error_class="transient",
            retryable=True,
            http_status=503,
        )

    def parse(self, *, document_id: str, default_text: str, parser_version: str) -> dict[str, object]:
        if not self._endpoint:
            return super().parse(
                document_id=document_id,
                default_text=default_text,
                parser_version=parser_version,
            )

        req_payload = {
            "document_id": document_id,
            "parser": self.name,
            "parser_version": parser_version or self.version,
            "default_text": default_text,
        }
        try:
            response_payload = _post_json(
                endpoint=self._endpoint,
                payload=req_payload,
                timeout_s=self._timeout_s,
            )
        except (TimeoutError, URLError, OSError, ValueError) as exc:
            raise ApiError(
                code="DOC_PARSE_UPSTREAM_UNAVAILABLE",
                message=f"{self.name} parser endpoint unavailable",
                error_class="transient",
                retryable=True,
                http_status=503,
            ) from exc

        if not isinstance(response_payload, Mapping):
            raise ApiError(
                code="DOC_PARSE_SCHEMA_INVALID",
                message=f"{self.name} parser response schema invalid",
                error_class="transient",
                retryable=True,
                http_status=503,
            )
        return self._chunk_from_response(
            payload=response_payload,
            document_id=document_id,
            parser_version=parser_version or self.version,
            default_text=default_text,
        )


class ParserAdapterRegistry:
    def __init__(self, adapters: dict[str, ParserAdapter]) -> None:
        self._adapters = adapters

    def parse_with_route(
        self,
        *,
        route: ParseRoute,
        document_id: str,
        default_text: str,
    ) -> dict[str, object]:
        candidates = [route.selected_parser, *route.fallback_chain]

        # SSOT §3 约束: fallback 链最多 2 跳
        # selected_parser + 最多 2 个 fallback = 最多 3 次尝试
        max_attempts = min(3, len(candidates))
        candidates = candidates[:max_attempts]

        last_error: ApiError | None = None
        for parser_name in candidates:
            adapter = self._adapters.get(parser_name)
            if adapter is None:
                continue
            try:
                return adapter.parse(
                    document_id=document_id,
                    default_text=default_text,
                    parser_version=route.parser_version,
                )
            except ApiError as exc:
                last_error = exc
                continue

        raise ApiError(
            code="PARSER_FALLBACK_EXHAUSTED",
            message=(
                f"no parser adapter available after {len(candidates)} attempts: {last_error.code}"
                if last_error is not None
                else "no parser adapter available"
            ),
            error_class="transient",
            retryable=True,
            http_status=503,
        )


def select_parse_route(*, filename: str, doc_type: str | None) -> ParseRoute:
    lower_name = filename.lower()
    office_or_html_suffixes = (".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".html", ".htm")
    if lower_name.endswith(".pdf"):
        return ParseRoute(selected_parser="mineru", fallback_chain=["docling", "ocr"])
    if lower_name.endswith(office_or_html_suffixes):
        return ParseRoute(selected_parser="docling", fallback_chain=["ocr"])
    if (doc_type or "").lower() in {"tender", "bid", "attachment"}:
        return ParseRoute(selected_parser="mineru", fallback_chain=["docling", "ocr"])
    return ParseRoute(selected_parser="ocr", fallback_chain=[])


def disabled_parsers_from_env(env: dict[str, str] | None = None) -> set[str]:
    source = os.environ if env is None else env
    raw = source.get("BEA_DISABLED_PARSERS", "")
    if not raw.strip():
        return set()
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


class LocalParserAdapter:
    """Parse files locally using pymupdf/python-docx without external service."""

    def __init__(self, *, name: str = "local", version: str = "v1") -> None:
        self.name = name
        self.version = version

    def parse(self, *, document_id: str, default_text: str, parser_version: str) -> dict[str, object]:
        return {
            "document_id": document_id,
            "pages": [1],
            "positions": [{"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0], "start": 0, "end": len(default_text)}],
            "section": "local_parsed",
            "heading_path": ["content"],
            "chunk_type": "text",
            "parser": self.name,
            "parser_version": parser_version or self.version,
            "content_source": "local",
            "text": default_text,
        }

    def parse_file(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        document_id: str,
    ) -> list[dict[str, object]]:
        from app.document_parser import parse_file_bytes

        return parse_file_bytes(
            file_bytes,
            filename=filename,
            document_id=document_id,
            parser_name=self.name,
            parser_version=self.version,
        )


def build_default_parser_registry(
    *,
    disabled_parsers: Iterable[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> ParserAdapterRegistry:
    source = os.environ if env is None else env
    disabled = {x.lower() for x in (disabled_parsers or ())}
    mineru_timeout = float(source.get("MINERU_TIMEOUT_S", "30") or "30")
    docling_timeout = float(source.get("DOCLING_TIMEOUT_S", "30") or "30")
    ocr_timeout = float(source.get("OCR_TIMEOUT_S", "30") or "30")

    use_local = source.get("BEA_PARSER_LOCAL_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}

    adapters: dict[str, ParserAdapter] = {
        "mineru": HttpParserAdapter(
            name="mineru",
            section="mineru_parsed",
            endpoint=source.get("MINERU_ENDPOINT", ""),
            timeout_s=mineru_timeout,
        ),
        "docling": HttpParserAdapter(
            name="docling",
            section="docling_parsed",
            endpoint=source.get("DOCLING_ENDPOINT", ""),
            timeout_s=docling_timeout,
        ),
        "ocr": HttpParserAdapter(
            name="ocr",
            section="ocr_fallback",
            endpoint=source.get("OCR_ENDPOINT", ""),
            timeout_s=ocr_timeout,
        ),
    }
    if use_local:
        adapters["local"] = LocalParserAdapter(name="local", version="v1")
    if disabled:
        adapters = {name: adapter for name, adapter in adapters.items() if name not in disabled}
    return ParserAdapterRegistry(adapters)
