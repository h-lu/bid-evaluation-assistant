"""SQL whitelist branch for structured field queries.

Spec: retrieval-and-scoring-spec §5.3
Only allows queries on whitelisted fields; rejects all others.
No arbitrary SQL concatenation. No cross-tenant JOINs.
"""

from __future__ import annotations

from typing import Any

WHITELIST_FIELDS: frozenset[str] = frozenset(
    {
        "supplier_code",
        "qualification_level",
        "registered_capital",
        "bid_price",
        "delivery_period",
        "warranty_period",
    }
)

_NUMERIC_FIELDS: frozenset[str] = frozenset(
    {
        "registered_capital",
        "bid_price",
        "delivery_period",
        "warranty_period",
    }
)

_STRING_FIELDS: frozenset[str] = frozenset(
    {
        "supplier_code",
        "qualification_level",
    }
)


def validate_structured_filters(filters: dict[str, Any]) -> dict[str, Any]:
    """Validate that all filter keys are in the whitelist.

    Returns validated filters dict.
    Raises ValueError for non-whitelisted fields.
    """
    if not isinstance(filters, dict):
        raise ValueError("structured_filters must be a dict")
    invalid = set(filters.keys()) - WHITELIST_FIELDS
    if invalid:
        raise ValueError(f"non-whitelisted fields: {sorted(invalid)}. Allowed: {sorted(WHITELIST_FIELDS)}")
    return dict(filters)


def _match_string_field(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(actual) == str(expected)


def _match_numeric_field(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    try:
        actual_num = float(actual)
    except (TypeError, ValueError):
        return False
    if isinstance(expected, dict):
        lo = expected.get("min")
        hi = expected.get("max")
        if lo is not None and actual_num < float(lo):
            return False
        if hi is not None and actual_num > float(hi):
            return False
        return lo is not None or hi is not None
    try:
        return actual_num == float(expected)
    except (TypeError, ValueError):
        return False


def _get_supplier_field(supplier: dict[str, Any], field: str) -> Any:
    """Resolve a whitelist field from a supplier dict.

    The supplier dict can store structured data in nested dicts like
    ``qualification`` (containing ``qualification_level``, ``registered_capital``)
    or at the top level. This helper checks both.
    """
    if field in supplier:
        return supplier[field]
    qual = supplier.get("qualification") or {}
    if isinstance(qual, dict) and field in qual:
        return qual[field]
    return None


def _supplier_matches(supplier: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field, expected in filters.items():
        actual = _get_supplier_field(supplier, field)
        if field in _NUMERIC_FIELDS:
            if not _match_numeric_field(actual, expected):
                return False
        else:
            if not _match_string_field(actual, expected):
                return False
    return True


def query_structured(
    *,
    store: Any,
    tenant_id: str,
    project_id: str,
    supplier_id: str,
    structured_filters: dict[str, Any],
) -> list[dict[str, Any]]:
    """Query structured data using ONLY whitelisted fields.

    Searches through the store's supplier metadata and document chunks
    for items matching the structured filters, while enforcing tenant isolation.

    Returns list of candidate dicts compatible with retrieval pipeline items:
    ``[{"chunk_id": ..., "score_raw": ..., "reason": "structured_match", "metadata": {...}}]``
    """
    validated = validate_structured_filters(structured_filters)
    if not validated:
        return []

    candidates: list[dict[str, Any]] = []
    matching_supplier_ids: set[str] = set()

    for sid, supplier in store.suppliers.items():
        if supplier.get("tenant_id") != tenant_id:
            continue
        if supplier_id and sid != supplier_id:
            continue
        if not _supplier_matches(supplier, validated):
            continue
        matching_supplier_ids.add(sid)

    if not matching_supplier_ids:
        return []

    seen_chunk_ids: set[str] = set()

    for chunk_id, source in store.citation_sources.items():
        if source.get("tenant_id") != tenant_id:
            continue
        if source.get("project_id") != project_id:
            continue
        if source.get("supplier_id") not in matching_supplier_ids:
            continue
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        candidates.append(
            {
                "chunk_id": chunk_id,
                "score_raw": 1.0,
                "reason": "structured_match",
                "metadata": {
                    "tenant_id": source.get("tenant_id"),
                    "project_id": source.get("project_id"),
                    "supplier_id": source.get("supplier_id"),
                    "document_id": source.get("document_id"),
                    "doc_type": source.get("doc_type"),
                    "page": int(source.get("page", 1)),
                    "bbox": source.get("bbox", [0, 0, 1, 1]),
                },
            }
        )

    for doc_id, chunks in store.document_chunks.items():
        doc = store.documents.get(doc_id, {})
        if doc.get("tenant_id") != tenant_id:
            continue
        if doc.get("project_id") != project_id:
            continue
        if doc.get("supplier_id") not in matching_supplier_ids:
            continue
        for chunk in chunks:
            cid = chunk.get("chunk_id")
            if not cid or cid in seen_chunk_ids:
                continue
            seen_chunk_ids.add(cid)
            page, bbox = 1, [0, 0, 1, 1]
            positions = chunk.get("positions", [])
            if isinstance(positions, list) and positions:
                first = positions[0] if isinstance(positions[0], dict) else {}
                page = int(first.get("page", 1))
                bbox_raw = first.get("bbox")
                if isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                    bbox = bbox_raw
            candidates.append(
                {
                    "chunk_id": cid,
                    "score_raw": 1.0,
                    "reason": "structured_match",
                    "metadata": {
                        "tenant_id": tenant_id,
                        "project_id": project_id,
                        "supplier_id": doc.get("supplier_id"),
                        "document_id": doc_id,
                        "doc_type": doc.get("doc_type"),
                        "page": page,
                        "bbox": bbox,
                    },
                }
            )

    return candidates
