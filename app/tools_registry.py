from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from jsonschema import ValidationError, validate


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    side_effect_level: str
    idempotency_policy: str
    timeout_retry_policy: str
    owner: str
    risk_level: str
    handler: Callable[[dict[str, Any]], dict[str, Any]] | None = None


_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> ToolSpec:
    _REGISTRY[spec.name] = spec
    return spec


def list_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def list_tool_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for spec in list_tools():
        specs.append(
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
                "output_schema": spec.output_schema,
                "side_effect_level": spec.side_effect_level,
                "idempotency_policy": spec.idempotency_policy,
                "timeout_retry_policy": spec.timeout_retry_policy,
                "owner": spec.owner,
                "risk_level": spec.risk_level,
            }
        )
    return specs


def get_tool(name: str) -> ToolSpec:
    if name not in _REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    return _REGISTRY[name]


def validate_input(spec: ToolSpec, payload: dict[str, Any]) -> None:
    validate(instance=payload, schema=spec.input_schema)


def validate_output(spec: ToolSpec, payload: dict[str, Any]) -> None:
    validate(instance=payload, schema=spec.output_schema)


def hash_payload(payload: dict[str, Any]) -> str:
    raw = repr(sorted(payload.items())).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def init_default_tools() -> None:
    if _REGISTRY:
        return
    register_tool(
        ToolSpec(
            name="dlq_discard",
            description="Discard a DLQ item with approvals.",
            input_schema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "reviewer_id": {"type": "string"},
                    "reviewer_id_2": {"type": ["string", "null"]},
                },
                "required": ["item_id", "reason", "reviewer_id"],
            },
            output_schema={
                "type": "object",
                "properties": {"item_id": {"type": "string"}, "status": {"type": "string"}},
                "required": ["item_id", "status"],
            },
            side_effect_level="external_commit",
            idempotency_policy="by_item_id",
            timeout_retry_policy="no_retry",
            owner="ops",
            risk_level="L3",
        )
    )
    register_tool(
        ToolSpec(
            name="legal_hold_release",
            description="Release a legal hold after dual approval.",
            input_schema={
                "type": "object",
                "properties": {
                    "hold_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "reviewer_id": {"type": "string"},
                    "reviewer_id_2": {"type": "string"},
                },
                "required": ["hold_id", "reason", "reviewer_id", "reviewer_id_2"],
            },
            output_schema={
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "status": {"type": "string"}},
                "required": ["hold_id", "status"],
            },
            side_effect_level="external_commit",
            idempotency_policy="by_hold_id",
            timeout_retry_policy="no_retry",
            owner="governance",
            risk_level="L3",
        )
    )


def require_tool(name: str) -> ToolSpec:
    init_default_tools()
    return get_tool(name)


def ensure_valid_input(spec: ToolSpec, payload: dict[str, Any]) -> None:
    try:
        validate_input(spec, payload)
    except ValidationError as exc:
        raise ValueError(f"tool input invalid: {exc.message}") from exc
