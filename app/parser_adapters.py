from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.errors import ApiError


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
                    "bbox": [100, 120, 520, 380],
                    "start": 0,
                    "end": 128,
                }
            ],
            "section": self._section,
            "heading_path": ["section-1", self.name],
            "chunk_type": "text",
            "parser": self.name,
            "parser_version": parser_version or self.version,
            "text": default_text,
        }


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
        for parser_name in candidates:
            adapter = self._adapters.get(parser_name)
            if adapter is None:
                continue
            return adapter.parse(
                document_id=document_id,
                default_text=default_text,
                parser_version=route.parser_version,
            )
        raise ApiError(
            code="PARSER_FALLBACK_EXHAUSTED",
            message="no parser adapter available",
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


def build_default_parser_registry() -> ParserAdapterRegistry:
    adapters: dict[str, ParserAdapter] = {
        "mineru": StubParserAdapter(name="mineru", section="mineru_parsed"),
        "docling": StubParserAdapter(name="docling", section="docling_parsed"),
        "ocr": StubParserAdapter(name="ocr", section="ocr_fallback"),
    }
    return ParserAdapterRegistry(adapters)
