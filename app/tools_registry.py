from __future__ import annotations

import hashlib
from dataclasses import dataclass
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable

from jsonschema import ValidationError, validate

from app.errors import ApiError


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
_CIRCUIT_STATE: dict[str, dict[str, float | int | None]] = {}


@dataclass(frozen=True)
class ToolCallPolicy:
    disabled_tools: set[str]
    disabled_risk_levels: set[str]
    timeout_s: float
    retry_max: int
    cb_failure_threshold: int
    cb_reset_s: int

    @classmethod
    def from_env(cls) -> "ToolCallPolicy":
        disabled_tools = {x.strip() for x in os.environ.get("TOOL_DISABLED", "").split(",") if x.strip()}
        disabled_risk_levels = {
            x.strip() for x in os.environ.get("TOOL_DISABLED_RISK_LEVELS", "").split(",") if x.strip()
        }
        timeout_ms = int(os.environ.get("TOOL_CALL_TIMEOUT_MS", "3000") or "3000")
        retry_max = int(os.environ.get("TOOL_CALL_RETRY_MAX", "0") or "0")
        cb_failure_threshold = int(os.environ.get("TOOL_CALL_CB_THRESHOLD", "3") or "3")
        cb_reset_s = int(os.environ.get("TOOL_CALL_CB_RESET_S", "60") or "60")
        return cls(
            disabled_tools=disabled_tools,
            disabled_risk_levels=disabled_risk_levels,
            timeout_s=max(0.001, timeout_ms / 1000.0),
            retry_max=max(0, retry_max),
            cb_failure_threshold=max(1, cb_failure_threshold),
            cb_reset_s=max(1, cb_reset_s),
        )


class ToolTimeoutError(RuntimeError):
    pass


def _circuit_state(name: str) -> dict[str, float | int | None]:
    state = _CIRCUIT_STATE.get(name)
    if state is None:
        state = {"failures": 0, "opened_at": None}
        _CIRCUIT_STATE[name] = state
    return state


def _is_circuit_open(name: str, *, policy: ToolCallPolicy) -> bool:
    state = _circuit_state(name)
    opened_at = state.get("opened_at")
    if opened_at is None:
        return False
    if time.monotonic() - float(opened_at) >= policy.cb_reset_s:
        state["opened_at"] = None
        state["failures"] = 0
        return False
    return True


def _record_failure(name: str, *, policy: ToolCallPolicy) -> None:
    state = _circuit_state(name)
    state["failures"] = int(state.get("failures", 0)) + 1
    if int(state["failures"]) >= policy.cb_failure_threshold:
        state["opened_at"] = time.monotonic()


def _record_success(name: str) -> None:
    state = _circuit_state(name)
    state["failures"] = 0
    state["opened_at"] = None


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


def execute_tool(
    spec: ToolSpec,
    *,
    input_payload: dict[str, Any],
    invoke: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    policy = ToolCallPolicy.from_env()
    if spec.name in policy.disabled_tools or spec.risk_level in policy.disabled_risk_levels:
        raise ApiError(
            code="TOOL_DISABLED",
            message=f"tool disabled: {spec.name}",
            error_class="security_sensitive",
            retryable=False,
            http_status=403,
        )
    try:
        validate_input(spec, input_payload)
    except ValidationError as exc:
        raise ApiError(
            code="TOOL_INPUT_INVALID",
            message=f"tool input invalid: {exc.message}",
            error_class="validation",
            retryable=False,
            http_status=400,
        ) from exc

    if _is_circuit_open(spec.name, policy=policy):
        raise ApiError(
            code="TOOL_CIRCUIT_OPEN",
            message=f"tool circuit open: {spec.name}",
            error_class="availability",
            retryable=True,
            http_status=503,
        )

    attempts = policy.retry_max + 1
    last_error: Exception | None = None
    saw_timeout = False
    for _ in range(attempts):
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(invoke)
                try:
                    result = future.result(timeout=policy.timeout_s)
                except FutureTimeoutError as exc:
                    future.cancel()
                    raise ToolTimeoutError("tool call timeout") from exc
            if not isinstance(result, dict):
                raise ApiError(
                    code="TOOL_OUTPUT_INVALID",
                    message="tool output must be object",
                    error_class="validation",
                    retryable=False,
                    http_status=500,
                )
            try:
                validate_output(spec, result)
            except ValidationError as exc:
                raise ApiError(
                    code="TOOL_OUTPUT_INVALID",
                    message=f"tool output invalid: {exc.message}",
                    error_class="validation",
                    retryable=False,
                    http_status=500,
                ) from exc
            _record_success(spec.name)
            return result
        except ToolTimeoutError as exc:
            _record_failure(spec.name, policy=policy)
            last_error = exc
            saw_timeout = True
            continue
        except ApiError as exc:
            if not exc.retryable:
                raise
            _record_failure(spec.name, policy=policy)
            last_error = exc
            continue
        except Exception as exc:
            _record_failure(spec.name, policy=policy)
            last_error = exc
            continue

    if saw_timeout:
        raise ApiError(
            code="TOOL_TIMEOUT",
            message=str(last_error or "tool call timeout"),
            error_class="availability",
            retryable=True,
            http_status=504,
        )
    raise ApiError(
        code="TOOL_EXECUTION_FAILED",
        message=str(last_error or "tool execution failed"),
        error_class="availability",
        retryable=True,
        http_status=500,
    )


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
                "properties": {"dlq_id": {"type": "string"}, "status": {"type": "string"}},
                "required": ["dlq_id", "status"],
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
    register_tool(
        ToolSpec(
            name="strategy_tuning_apply",
            description="Apply strategy tuning with approval.",
            input_schema={
                "type": "object",
                "properties": {
                    "release_id": {"type": "string"},
                    "selector": {"type": "object"},
                    "score_calibration": {"type": "object"},
                    "tool_policy": {"type": "object"},
                },
                "required": ["release_id", "selector", "score_calibration", "tool_policy"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "strategy_version": {"type": "string"},
                    "selector": {"type": "object"},
                    "score_calibration": {"type": "object"},
                    "tool_policy": {"type": "object"},
                },
                "required": ["strategy_version", "selector", "score_calibration", "tool_policy"],
            },
            side_effect_level="state_write",
            idempotency_policy="by_release_id",
            timeout_retry_policy="no_retry",
            owner="ops",
            risk_level="L2",
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
