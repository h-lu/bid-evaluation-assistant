"""Constraint extraction from queries: entity, numeric, time.

Spec: retrieval-and-scoring-spec §3.2
  1. entity_constraints
  2. numeric_constraints
  3. time_constraints
  4. must_include_terms  (handled externally)
  5. must_exclude_terms  (handled externally)
"""

from __future__ import annotations

import re
from typing import Any


def extract_constraints(query: str) -> dict[str, list[dict[str, Any]]]:
    """Extract structured constraints from *query*."""
    return {
        "entity_constraints": _extract_entities(query),
        "numeric_constraints": _extract_numerics(query),
        "time_constraints": _extract_times(query),
    }


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

_COMPANY_RE = re.compile(
    r"[\u4e00-\u9fff]{2,20}"
    r"(?:有限|股份|集团|科技|建设|工程|投资|贸易|咨询|设计|物流|电子|信息|通信|能源|环保|医药|食品)"
    r"(?:责任)?公司"
)

_QUALIFICATION_RE = re.compile(
    r"(?:特级|一级|二级|三级|四级|甲级|乙级|丙级|丁级)"
    r"(?:资质|资格|等级)?"
)

_CERT_RE = re.compile(
    r"(?:ISO\s*\d{4,5}(?::\d{4})?|GB/?T?\s*\d{4,5}|CCC|3C|CE)"
)


def _extract_entities(query: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    for m in _COMPANY_RE.finditer(query):
        entities.append({"type": "company", "value": m.group()})
    for m in _QUALIFICATION_RE.finditer(query):
        entities.append({"type": "qualification", "value": m.group()})
    for m in _CERT_RE.finditer(query):
        entities.append({"type": "certification", "value": m.group()})
    return entities


# ---------------------------------------------------------------------------
# Numeric extraction
# ---------------------------------------------------------------------------

_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万元|亿元|元|万)")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[~\-到至]\s*(\d+(?:\.\d+)?)")
_MIN_BOUND_RE = re.compile(r"(?:不少于|不低于|至少|大于等于|>=?)\s*(\d+(?:\.\d+)?)")
_MAX_BOUND_RE = re.compile(r"(?:不超过|不高于|最多|小于等于|<=?)\s*(\d+(?:\.\d+)?)")

_UNIT_MULTIPLIER = {"万元": 10_000, "万": 10_000, "亿元": 100_000_000, "元": 1}


def _extract_numerics(query: str) -> list[dict[str, Any]]:
    numerics: list[dict[str, Any]] = []
    for m in _AMOUNT_RE.finditer(query):
        unit = m.group(2)
        numerics.append({
            "type": "amount",
            "value": float(m.group(1)) * _UNIT_MULTIPLIER.get(unit, 1),
            "unit": "元",
            "raw": m.group(),
        })
    for m in _PERCENT_RE.finditer(query):
        numerics.append({
            "type": "percentage",
            "value": float(m.group(1)),
            "unit": "%",
            "raw": m.group(),
        })
    for m in _RANGE_RE.finditer(query):
        numerics.append({
            "type": "range",
            "min": float(m.group(1)),
            "max": float(m.group(2)),
            "raw": m.group(),
        })
    for m in _MIN_BOUND_RE.finditer(query):
        numerics.append({
            "type": "min_bound",
            "value": float(m.group(1)),
            "raw": m.group(),
        })
    for m in _MAX_BOUND_RE.finditer(query):
        numerics.append({
            "type": "max_bound",
            "value": float(m.group(1)),
            "raw": m.group(),
        })
    return numerics


# ---------------------------------------------------------------------------
# Time extraction
# ---------------------------------------------------------------------------

_ISO_DATE_RE = re.compile(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})")
_CN_DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(?:(\d{1,2})日)?")
_DURATION_RE = re.compile(r"(\d+)\s*(?:个)?(天|日|周|月|年)")
_DEADLINE_RE = re.compile(r"(\d+)\s*(?:个)?(?:工作日|天|日|月|年)\s*(?:以?内|之内)")


def _extract_times(query: str) -> list[dict[str, Any]]:
    times: list[dict[str, Any]] = []
    for m in _ISO_DATE_RE.finditer(query):
        times.append({
            "type": "date",
            "value": f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}",
            "raw": m.group(),
        })
    for m in _CN_DATE_RE.finditer(query):
        day = m.group(3) or "01"
        times.append({
            "type": "date",
            "value": f"{m.group(1)}-{m.group(2).zfill(2)}-{day.zfill(2)}",
            "raw": m.group(),
        })
    for m in _DEADLINE_RE.finditer(query):
        times.append({
            "type": "deadline",
            "value": int(m.group(1)),
            "raw": m.group(),
        })
    seen_deadline_spans = {m.span() for m in _DEADLINE_RE.finditer(query)}
    for m in _DURATION_RE.finditer(query):
        if m.span() not in seen_deadline_spans and not any(
            s[0] <= m.start() and m.end() <= s[1] for s in seen_deadline_spans
        ):
            times.append({
                "type": "duration",
                "value": int(m.group(1)),
                "unit": m.group(2),
                "raw": m.group(),
            })
    return times
