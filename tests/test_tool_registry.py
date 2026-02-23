from app.tools_registry import ensure_valid_input, require_tool


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
