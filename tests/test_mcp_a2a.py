import pytest

from app.mcp_a2a import enforce_mcp_baseline, validate_a2a_result
from app.errors import ApiError


def test_mcp_baseline_rejects_missing_service():
    with pytest.raises(ApiError):
        enforce_mcp_baseline(payload={"session_id": "s1"}, tenant_id="t1")


def test_mcp_baseline_accepts_scopes():
    payload = {"service": "kb", "session_id": "s1", "scopes": ["read"]}
    assert enforce_mcp_baseline(payload=payload, tenant_id="t1") == payload


def test_a2a_result_rejects_invalid_status():
    with pytest.raises(ApiError):
        validate_a2a_result(payload={"task_id": "t1", "status": "oops"})


def test_a2a_result_accepts_success():
    payload = {"task_id": "t1", "status": "succeeded", "result": {"ok": True}}
    assert validate_a2a_result(payload=payload) == payload
