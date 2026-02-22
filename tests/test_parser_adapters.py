from __future__ import annotations

import pytest

from app.errors import ApiError
from app.parser_adapters import build_default_parser_registry, select_parse_route


def test_select_parse_route_by_filename_and_doc_type():
    pdf_route = select_parse_route(filename="proposal.pdf", doc_type="bid")
    assert pdf_route.selected_parser == "mineru"
    assert pdf_route.fallback_chain == ["docling", "ocr"]
    assert pdf_route.parser_version == "v0"

    docx_route = select_parse_route(filename="proposal.docx", doc_type="attachment")
    assert docx_route.selected_parser == "docling"
    assert docx_route.fallback_chain == ["ocr"]
    assert docx_route.parser_version == "v0"

    unknown_route = select_parse_route(filename="scan.bin", doc_type=None)
    assert unknown_route.selected_parser == "ocr"
    assert unknown_route.fallback_chain == []
    assert unknown_route.parser_version == "v0"


def test_default_parser_registry_builds_chunk_payload():
    registry = build_default_parser_registry()
    route = select_parse_route(filename="proposal.pdf", doc_type="bid")

    chunk = registry.parse_with_route(
        route=route,
        document_id="doc_parser_1",
        default_text="hello parser",
    )

    assert chunk["document_id"] == "doc_parser_1"
    assert chunk["chunk_type"] == "text"
    assert chunk["parser"] == "mineru"
    assert chunk["parser_version"] == "v0"
    assert chunk["text"] == "hello parser"
    assert chunk["pages"] == [1]
    assert chunk["positions"][0]["bbox"] == [100, 120, 520, 380]


def test_registry_falls_back_when_selected_parser_disabled():
    registry = build_default_parser_registry(disabled_parsers={"mineru"})
    route = select_parse_route(filename="proposal.pdf", doc_type="bid")

    chunk = registry.parse_with_route(
        route=route,
        document_id="doc_parser_fallback",
        default_text="fallback text",
    )

    assert chunk["parser"] == "docling"
    assert chunk["parser_version"] == "v0"


def test_registry_raises_when_all_parsers_disabled():
    registry = build_default_parser_registry(disabled_parsers={"mineru", "docling", "ocr"})
    route = select_parse_route(filename="proposal.pdf", doc_type="bid")

    with pytest.raises(ApiError) as exc:
        registry.parse_with_route(
            route=route,
            document_id="doc_parser_fail",
            default_text="x",
        )

    assert exc.value.code == "PARSER_FALLBACK_EXHAUSTED"
