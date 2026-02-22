from __future__ import annotations

from typing import Iterable

from app.errors import ApiError


def _raise_bbox_error(message: str) -> None:
    raise ApiError(
        code="MINERU_BBOX_FORMAT_INVALID",
        message=message,
        error_class="permanent",
        retryable=False,
        http_status=422,
    )


def select_content_source(files: Iterable[str]) -> str | None:
    names = list(files)
    for name in names:
        if name.endswith("content_list.json"):
            return name
    for name in names:
        if name.endswith("context_list.json"):
            return name
    return None


def normalize_bbox(bbox: list[float | int], force_format: str | None = None) -> list[float]:
    if len(bbox) != 4:
        _raise_bbox_error("bbox requires 4 numbers")

    try:
        x0 = float(bbox[0])
        y0 = float(bbox[1])
        v2 = float(bbox[2])
        v3 = float(bbox[3])
    except (TypeError, ValueError):
        _raise_bbox_error("bbox must contain numeric values")

    if force_format == "xyxy":
        if v2 > x0 and v3 > y0:
            return [x0, y0, v2, v3]
        _raise_bbox_error("invalid xyxy bbox")

    if force_format == "xywh":
        if v2 > 0 and v3 > 0:
            return [x0, y0, x0 + v2, y0 + v3]
        _raise_bbox_error("invalid xywh bbox")

    if v2 > x0 and v3 > y0:
        return [x0, y0, v2, v3]

    if v2 > 0 and v3 > 0:
        return [x0, y0, x0 + v2, y0 + v3]

    _raise_bbox_error("bbox format cannot be determined")


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(ch for ch in normalized if ch in {"\n", "\t"} or ord(ch) >= 32)


def decode_text_with_fallback(raw: bytes) -> str:
    for encoding in ("utf-8", "gb18030"):
        try:
            return _normalize_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue

    raise ApiError(
        code="TEXT_ENCODING_UNSUPPORTED",
        message="text encoding unsupported",
        error_class="permanent",
        retryable=False,
        http_status=422,
    )
