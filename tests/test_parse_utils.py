import pytest

from app.errors import ApiError
from app.parse_utils import decode_text_with_fallback, normalize_bbox, select_content_source


def test_select_content_source_prefers_content_list():
    files = ["a_context_list.json", "z_content_list.json", "full.md"]
    assert select_content_source(files) == "z_content_list.json"


def test_select_content_source_falls_back_to_context_list():
    files = ["x_context_list.json", "full.md"]
    assert select_content_source(files) == "x_context_list.json"


def test_select_content_source_5_level_priority():
    """SSOT §2.3: 文件发现 5 级优先级."""
    # 级别 1: *_content_list.json 优先
    files = ["a_context_list.json", "z_content_list.json", "full.md", "other.md", "x_middle.json"]
    assert select_content_source(files) == "z_content_list.json"

    # 级别 2: *context_list.json (无 content_list 时)
    files = ["a_context_list.json", "full.md", "other.md", "x_middle.json"]
    assert select_content_source(files) == "a_context_list.json"

    # 级别 3: full.md (无 content_list/context_list 时)
    files = ["full.md", "other.md", "x_middle.json"]
    assert select_content_source(files) == "full.md"

    # 级别 4: *.md (无 full.md 时)
    files = ["other.md", "x_middle.json"]
    assert select_content_source(files) == "other.md"

    # 级别 5: *_middle.json (无 md 时)
    files = ["x_middle.json", "y_middle.json"]
    assert select_content_source(files) == "x_middle.json"

    # 无匹配
    files = ["unknown.txt", "data.bin"]
    assert select_content_source(files) is None


def test_decode_text_with_fallback_supports_utf8_and_gb18030():
    assert decode_text_with_fallback("中文-utf8".encode()) == "中文-utf8"
    gb_bytes = "中文-gb".encode("gb18030")
    assert decode_text_with_fallback(gb_bytes) == "中文-gb"


def test_decode_text_with_fallback_raises_error_for_unknown_encoding():
    with pytest.raises(ApiError) as exc:
        decode_text_with_fallback(b"\xff\xfe\xfa\xfb")

    assert exc.value.code == "TEXT_ENCODING_UNSUPPORTED"
    assert exc.value.http_status == 422


def test_normalize_bbox_supports_xyxy_and_xywh():
    assert normalize_bbox([1, 2, 11, 22]) == [1.0, 2.0, 11.0, 22.0]
    assert normalize_bbox([1, 2, 10, 20], force_format="xywh") == [1.0, 2.0, 11.0, 22.0]


def test_normalize_bbox_rejects_invalid_values():
    with pytest.raises(ApiError) as exc:
        normalize_bbox([1, 2, 0, -1])
    assert exc.value.code == "MINERU_BBOX_FORMAT_INVALID"
    assert exc.value.http_status == 422
