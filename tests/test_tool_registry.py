import pytest

from app.errors import ApiError
from app.tools_registry import ToolSpec, ensure_valid_input, execute_tool, register_tool, require_tool


def test_tool_registry_validation_rejects_missing_fields():
    tool = require_tool("dlq_discard")
    try:
        ensure_valid_input(tool, {"item_id": "dlq_1"})
    except ValueError as exc:
        assert "reason" in str(exc)
    else:
        raise AssertionError("expected validation error")


def test_tool_registry_accepts_valid_payload():
    tool = require_tool("legal_hold_release")
    payload = {
        "hold_id": "hold_1",
        "reason": "test",
        "reviewer_id": "u1",
        "reviewer_id_2": "u2",
    }
    ensure_valid_input(tool, payload)


def test_execute_tool_blocks_disabled(monkeypatch):
    tool = require_tool("dlq_discard")
    monkeypatch.setenv("TOOL_DISABLED", "dlq_discard")
    with pytest.raises(ApiError) as exc:
        execute_tool(
            tool,
            input_payload={"item_id": "dlq_1", "reason": "x", "reviewer_id": "a", "reviewer_id_2": "b"},
            invoke=lambda: {"dlq_id": "dlq_1", "status": "discarded"},
        )
    assert exc.value.code == "TOOL_DISABLED"


def test_execute_tool_output_validation(monkeypatch):
    tool = ToolSpec(
        name="test_output",
        description="test output validation",
        input_schema={"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        side_effect_level="read_only",
        idempotency_policy="none",
        timeout_retry_policy="no_retry",
        owner="test",
        risk_level="L0",
    )
    register_tool(tool)
    with pytest.raises(ApiError) as exc:
        execute_tool(
            tool,
            input_payload={"value": "x"},
            invoke=lambda: {"unexpected": True},
        )
    assert exc.value.code == "TOOL_OUTPUT_INVALID"


def test_execute_tool_timeout(monkeypatch):
    tool = ToolSpec(
        name="test_timeout",
        description="test timeout",
        input_schema={"type": "object", "properties": {}, "required": []},
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        side_effect_level="read_only",
        idempotency_policy="none",
        timeout_retry_policy="no_retry",
        owner="test",
        risk_level="L0",
    )
    register_tool(tool)
    monkeypatch.setenv("TOOL_CALL_TIMEOUT_MS", "10")

    def _slow():
        import time

        time.sleep(0.05)
        return {"ok": True}

    with pytest.raises(ApiError) as exc:
        execute_tool(tool, input_payload={}, invoke=_slow)
    assert exc.value.code == "TOOL_TIMEOUT"


def test_strategy_tuning_tool_spec_schema():
    tool = require_tool("strategy_tuning_apply")
    payload = {
        "release_id": "rel_1",
        "selector": {"mode": "hybrid"},
        "score_calibration": {"offset": 0.1},
        "tool_policy": {"allowed_tools": ["retrieval"]},
    }
    ensure_valid_input(tool, payload)
