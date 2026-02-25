"""Tests for SSOT §3 fallback 2-hop limit."""

import pytest

from app.errors import ApiError
from app.parser_adapters import (
    ParserAdapterRegistry,
    ParseRoute,
    StubParserAdapter,
)


class AlwaysFailAdapter(StubParserAdapter):
    """Adapter that always fails."""

    def parse(self, **kwargs):
        raise ApiError(
            code="PARSE_FAILED",
            message="intentional failure",
            error_class="transient",
            retryable=True,
            http_status=503,
        )


def test_fallback_chain_limited_to_2_hops():
    """SSOT §3: fallback 链最多 2 跳 (selected + 2 fallbacks = 3 次尝试)."""
    # 4 个候选，只有最后一个能成功
    adapters = {
        "a": AlwaysFailAdapter(name="a", section="a"),
        "b": AlwaysFailAdapter(name="b", section="b"),
        "c": AlwaysFailAdapter(name="c", section="c"),
        "d": StubParserAdapter(name="d", section="d"),  # 这个能成功
    }
    registry = ParserAdapterRegistry(adapters)

    route = ParseRoute(
        selected_parser="a",
        fallback_chain=["b", "c", "d"],  # 4 个候选
        parser_version="v1",
    )

    # SSOT 约束: 只尝试前 3 个 (a, b, c)，d 不应被尝试
    with pytest.raises(ApiError) as exc_info:
        registry.parse_with_route(
            route=route,
            document_id="doc_1",
            default_text="test",
        )
    assert exc_info.value.code == "PARSER_FALLBACK_EXHAUSTED"
    assert "3 attempts" in exc_info.value.message


def test_fallback_succeeds_within_2_hops():
    """When success is within 2 hops, should return result."""
    adapters = {
        "a": AlwaysFailAdapter(name="a", section="a"),
        "b": StubParserAdapter(name="b", section="b"),  # 第 2 个成功
        "c": StubParserAdapter(name="c", section="c"),
    }
    registry = ParserAdapterRegistry(adapters)

    route = ParseRoute(
        selected_parser="a",
        fallback_chain=["b", "c"],
        parser_version="v1",
    )

    result = registry.parse_with_route(
        route=route,
        document_id="doc_1",
        default_text="test",
    )

    assert result["parser"] == "b"
